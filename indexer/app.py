import pdfplumber
from config import get_config
import re
from openai import AzureOpenAI
from azure.cosmos import CosmosClient, ContainerProxy
import getopt
import sys
from pathlib import Path 
import json
from PIL import Image
from io import BytesIO
from pdf2image import convert_from_path
import uuid
import pytesseract
import cv2
import numpy as np
import pandas as pd
from typing import List, Tuple

def normalize_text(text: str):
    text = re.sub(r' {2,}',  ' ', text).strip()
    text = re.sub(r". ,","",text)
    # remove all instances of multiple spaces
    text = text.replace("..",".")
    text = text.replace(". .",".")
    if get_config("RemoveNewlinesDuringNormalization"):
        text = text.replace("\n", "")
        text = text.replace("\r", "")

    # replace unicode characters with more usable characters 
    text = text.replace("●", "*")
    text = text.replace("‑", "-")
    text = text.strip()
    
    return text

def strip_emails_and_phone_numbers_and_web_addresses(text):
    text = re.sub(r'(?:[a-zA-Z]|\d|\-|\.)*@cms\.hhs\.gov', "", text).strip()
    text = re.sub(r'\(?\d{3}\)?\-?\d{3}\-\d{4}', "", text).strip()
    text = re.sub(r'(https?|ftp):\/\/([a-zA-Z0-9\-.]+)(\/[^\s]*)?(\?[^\s]*)?', "", text).strip()

    return text

def generate_embeddings(client: AzureOpenAI, text: str):
    return client.embeddings.create(input = [text], model = get_config("EmbeddingsModel")).data[0].embedding

def get_cosmos_container():
    client = CosmosClient(get_config("COSMOS_DB_URL"), get_config("COSMOS_DB_KEY"))
    database = client.get_database_client(get_config("DATABASE_NAME"))
    container = database.get_container_client(get_config("CONTAINER_NAME"))
    return container

def create_document(cosmos_container: ContainerProxy, text: str, embeddings: list[float], chunk_number: int, model_type: str, document_type: str):
    item = {
        "id": f"{document_type}_{chunk_number}",
        "modelType": model_type,
        "text": text,
        "vector": embeddings,
        "documentType": document_type,
        "partitionKey": model_type
    }
    cosmos_container.upsert_item(item)

def upload_fact_sheet(): 
    print('Uploading Fact Sheet')

    cosmos_container = get_cosmos_container()

    openai_client = AzureOpenAI(
        api_key = get_config("AZURE_OPENAI_API_KEY"),
        api_version = "2024-02-01",
        azure_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
    )

    fact_sheet = get_config("FactSheetLocation")
    
    with pdfplumber.open(fact_sheet) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            page.flush_cache()
            normalized_page_text = normalize_text(page_text)

            embeddings = generate_embeddings(openai_client, normalized_page_text)

            partition_key = get_config("PartitionKey")
            print(f"Saving page {i+1}")
            create_document(cosmos_container, normalized_page_text, embeddings, i, partition_key, "FactSheet")

def delete_document_type(document_type: str):
    print(f'Deleting document {document_type}')
    cosmos_container = get_cosmos_container()
    partition_key = get_config("PartitionKey")
    partition_key = partition_key
    query = f"SELECT * FROM c WHERE c.partitionKey = '{partition_key}' AND c.documentType = '{document_type}'"
    items = cosmos_container.query_items(query=query, enable_cross_partition_query=False)
    deleted_count = 0
    for item in items:
        try:
            cosmos_container.delete_item(item=item['id'], partition_key=partition_key)
            deleted_count += 1
        except Exception as e:
            print(f"Failed to delete item {item['id']}: {str(e)}")

        if deleted_count % 100 == 0:
            print(f'Deleted {deleted_count} items')
    
    print(f'Deleted {deleted_count} items')

def chunk_text(text, openai_client):
    if get_config("UseAIChunking"):
        messages = [{
            "role": "user",
            "content": f'''
                Take the following "Text:" and break it into logically grouped chunks, ensuring each chunk maintains contextual meaning. 
                    * Keep all original text intact. Separate the chunks using |||| as a delimiter, outputting the result as a single line. 
                    * Do not add extra characters or summaries, —just return the original text chunked appropriately.  
                    * Remove any chunks that aren't necessary for RAG. 
                    * Remove any emails, phone numbers, web addresses.
                    * If there is no text provided then simply respond with "No Chunks"

                Text:
                {text}
            ''',
        }]

        chat_completion = openai_client.chat.completions.create(
            messages=messages,
            model=get_config("ChatModel")
        )

        chunked_text = chat_completion.choices[0].message.content.strip()
        return chunked_text.split("||||") if chunked_text != "No Chunks" else ""
    
    normalized_page_text = strip_emails_and_phone_numbers_and_web_addresses(text)
    normalized_page_text = normalize_text(text)
    return normalized_page_text.split(get_config("ChunkingCharacter"))

def attempt_to_extract_tables(image):
    def preprocess_image(image: np.ndarray) -> np.ndarray:
        """
        Preprocess the image to improve OCR accuracy.
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply thresholding to preprocess the image
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY
            | cv2.THRESH_OTSU)[1]

        # Apply dilation to merge letters
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
        dilate = cv2.dilate(thresh, kernel, iterations=1)

        return dilate

    def detect_table_borders(
        preprocessed_image: np.ndarray) -> Tuple[List[int], List[int]]:
        """
        Detect table borders using image processing techniques.
        """
        # Find all contours
        contours, _ = cv2.findContours(preprocessed_image,
            cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # Sort contours by area, descending
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        # Find the contour with 4 corners (assuming it's the table)
        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)

            if len(approx) == 4:
                # These are our table boundaries
                return approx.reshape(4, 2)

        return None

    def extract_table_structure(image: np.ndarray,
        table_coords: List[Tuple[int, int]]) -> pd.DataFrame:
        """
        Extract table structure using the detected table coordinates.
        """
        # Crop the table from the image
        x, y, w, h = cv2.boundingRect(np.array(table_coords))
        cropped = image[y:y+h, x:x+w]

        # Use Tesseract to do OCR on the cropped image
        ocr_result = pytesseract.image_to_data(cropped,
            output_type=pytesseract.Output.DATAFRAME)

        # Filter out empty text
        ocr_result = ocr_result[ocr_result.text.notna()]

        # Group by lines
        lines = ocr_result.groupby('block_num')

        # Extract text and positions
        table_data = []
        for _, line in lines:
            line_text = ' '.join(line['text'].tolist())
            left = line['left'].min()
            top = line['top'].min()
            table_data.append((line_text, left, top))

        # Sort by vertical position (top)
        table_data.sort(key=lambda x: x[2])

        # Create DataFrame
        df = pd.DataFrame(table_data, columns=['text', 'left', 'top'])

        # Identify columns based on 'left' position
        df['column'] = pd.cut(df['left'], bins=5, labels=False)

        # Pivot to create final table structure
        final_table = df.pivot(columns='column',
            values='text').reset_index(drop=True)

        return final_table
    
    np_image = np.array(image)

    # Preprocess the image
    preprocessed = preprocess_image(np_image)

    # Detect table borders
    table_coords = detect_table_borders(preprocessed)

    extracted_tables = []
    if table_coords is not None:
        # Extract table structure
        table = extract_table_structure(np_image, table_coords)
        extracted_tables.append(table.to_markdown(index=False))

    return extracted_tables

def adjust_image_for_ocr(image):
    np_image = np.array(image)
    # Convert to grayscale
    gray = cv2.cvtColor(np_image, cv2.COLOR_BGR2GRAY)
    
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY
        | cv2.THRESH_OTSU)[1]


    return thresh

def index_using_pdf_to_image(document, chunk_size, spooling_size, cosmos_container, overlap_size, openai_client, total_chunks, total_chunks_uploaded):    
    chunk_accumulator = []
    text_accumulator = []

    run_directory_name = str(uuid.uuid4())
    run_directory_path = Path(get_config("TempImageLocation")).joinpath(run_directory_name)
    raw_directory_path = run_directory_path.joinpath("raw")
    raw_directory_path.mkdir(exist_ok=True, parents=True)

    print(f'Converting pages to image here: {raw_directory_path}')
    images = convert_from_path(document["Location"], output_folder=raw_directory_path)
    print(f"Created {len(images)} image pages")
    for i, page_image in enumerate(images):
        print(f"Processing page {i+1}")


        page_image.save(run_directory_path.joinpath(f"page_{i+1}.png"), "PNG")
        adjusted_image = adjust_image_for_ocr(page_image)
        im = Image.fromarray(adjusted_image)
        im.save(run_directory_path.joinpath(f"page_{i+1}_adjusted.png"))
        text = pytesseract.image_to_string(adjusted_image)
        with open(run_directory_path.joinpath(f"page_text_raw_{i+1}.txt"), "w") as w:
            w.write(text) 

        normalized_text = normalize_text(text)

        with open(run_directory_path.joinpath(f"page_text_normalized_{i+1}.txt"), "w") as w:
            w.write(normalized_text) 

        normalized_text = normalized_text.strip()
        if len(normalized_text) <= 3:
            print(f"Skipping page, there is probably nothing of value to index. Text: '{normalized_text}'")
            continue

        chunks = chunk_text(normalized_text, openai_client)
        
        with open(run_directory_path.joinpath(f"page_text_chunks_{i+1}.txt"), "w") as w:
            w.write(json.dumps(chunks)) 
            
        if len(chunks) <= 3:
            print(f"QUALITY CONTROL!!!!")
            print(f"Only {len(chunks)} Chunks Found. Chunks: {chunks}")

        for text_chunk in chunks:
            cleaned_up_text = text_chunk.strip()
            # we don't want to index empty strings
            if len(cleaned_up_text) == 0:
                continue

            text_accumulator.append(f'<Chunk><DocumentName>{document["Name"]}</DocumentName><DocumentDescription>{document["Description"]}</DocumentDescription><Page>{i+1}</Page><Text>{cleaned_up_text}</Text></Chunk>')
            if len(text_accumulator) > chunk_size:
                chunk_accumulator.append(text_accumulator)
                total_chunks+=1
                text_accumulator = []
            
            if len(chunk_accumulator) == spooling_size:
                overlap_and_upload_chunks(cosmos_container, chunk_accumulator, overlap_size, openai_client, True, total_chunks, total_chunks_uploaded, '')
                total_chunks_uploaded+=(len(chunk_accumulator)-1)
                chunk_accumulator = chunk_accumulator[(spooling_size-1):]
    
    if len(text_accumulator) != 0:
        chunk_accumulator.append(text_accumulator)
        total_chunks+=1
        text_accumulator = []
    
    overlap_and_upload_chunks(cosmos_container, chunk_accumulator, overlap_size, openai_client, False, total_chunks, total_chunks_uploaded, '')

    if get_config("CleanupTempData"):
        run_directory_path.unlink() # delete run directory
    
    return (total_chunks, total_chunks_uploaded)

def index_using_pdfplumber(document, chunk_size, spooling_size, cosmos_container, overlap_size, openai_client, total_chunks, total_chunks_uploaded):
    chunk_accumulator = []
    text_accumulator = []

    with pdfplumber.open(document["Location"]) as pdf:
        print(f"Found {len(pdf.pages)} pages to index")
        for i, page in enumerate(pdf.pages):
            print(f"Processing {i+1} page")

            page_text = page.extract_text()
            page.flush_cache()
            
            chunks = chunk_text(page_text, openai_client)
            for text in chunks:
                cleaned_up_text = text.strip()
                # we don't want to index empty strings
                if len(cleaned_up_text) == 0:
                    continue

                text_accumulator.append(f'<Chunk><DocumentName>{document["Name"]}</DocumentName><DocumentDescription>{document["Description"]}</DocumentDescription><Page>{i+1}</Page><Text>{cleaned_up_text}</Text></Chunk>')
                if len(text_accumulator) > chunk_size:
                    chunk_accumulator.append(text_accumulator)
                    total_chunks+=1
                    text_accumulator = []
                
                if len(chunk_accumulator) == spooling_size:
                    overlap_and_upload_chunks(cosmos_container, chunk_accumulator, overlap_size, openai_client, True, total_chunks, total_chunks_uploaded, '')
                    total_chunks_uploaded+=(len(chunk_accumulator)-1)
                    chunk_accumulator = chunk_accumulator[(spooling_size-1):]
        
        if len(text_accumulator) != 0:
            chunk_accumulator.append(text_accumulator)
            total_chunks+=1
            text_accumulator = []
        
        overlap_and_upload_chunks(cosmos_container, chunk_accumulator, overlap_size, openai_client, False, total_chunks, total_chunks_uploaded, '')

    return (total_chunks, total_chunks_uploaded)
            
def upload_final_ruling():
    print('Uploading Final Ruling')

    openai_client = AzureOpenAI(
        api_key = get_config("AZURE_OPENAI_API_KEY"),
        api_version = "2024-02-01",
        azure_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
    )

    cosmos_container = get_cosmos_container()

    chunk_size = get_config("ChunkSize")
    overlap_size = get_config("Overlap")

    documents = get_config("Documents")

    print(f'Found {len(documents)} document(s) to index')

    spooling_size = get_config("SpoolingSize")

    partition_key = get_config("PartitionKey")
    print(f"Targeting {partition_key} partition")
    
    total_chunks = 0
    total_chunks_uploaded = get_config("StartingChunkCount") if get_config("StartingChunkCount") is not None else 0 

    for document in documents:   
        print(f"Processing '{document['Name']}'")
        if get_config("ConvertToImagesFirst"):
            (final_total_chunks, final_total_chunks_uploaded) = index_using_pdf_to_image(document, chunk_size, spooling_size, cosmos_container, overlap_size, openai_client, total_chunks, total_chunks_uploaded)
            total_chunks = final_total_chunks
            total_chunks_uploaded = final_total_chunks_uploaded
        else:
            (final_total_chunks, final_total_chunks_uploaded) = index_using_pdfplumber(document, chunk_size, spooling_size, cosmos_container, overlap_size, openai_client, total_chunks, total_chunks_uploaded)
            total_chunks = final_total_chunks
            total_chunks_uploaded = final_total_chunks_uploaded
        

def overlap_and_upload_chunks(cosmos_container, chunk_accumulator, overlap_size, openai_client, ignore_last_index, total_chunks, total_already_uploaded, joining_character):
    overlapped_chunks = []
    if len(chunk_accumulator) > 1:
        for i, chunk in enumerate(chunk_accumulator):
            if i == 0:
                if len(chunk_accumulator[i + 1]) < overlap_size:
                    overlapped_chunks.append(chunk + chunk_accumulator[i + 1])
                else:
                    overlapped_chunks.append(chunk + chunk_accumulator[i + 1][:overlap_size])
            elif i == len(chunk_accumulator) - 1:
                if ignore_last_index:
                    continue
                if len(chunk_accumulator[i - 1]) < overlap_size:
                    overlapped_chunks.append(chunk_accumulator[i - 1] + chunk)
                else:
                    overlapped_chunks.append(chunk_accumulator[i - 1][(-1 *overlap_size):] + chunk)
            else:
                new_chunk = None
                if len(chunk_accumulator[i - 1]) < overlap_size:
                    new_chunk = chunk_accumulator[i - 1] + chunk
                else:
                    new_chunk = chunk_accumulator[i - 1][(-1 *overlap_size):] + chunk

                if len(chunk_accumulator[i + 1]) < overlap_size:
                    new_chunk = new_chunk + chunk_accumulator[i + 1]
                else:
                    new_chunk = new_chunk + chunk_accumulator[i + 1][:overlap_size]

                overlapped_chunks.append(new_chunk)
    elif len(chunk_accumulator) == 1:
        # means there aren't enough chunks to overlap so just upload the one
        overlapped_chunks.append(chunk_accumulator[0])

    print(f"Overlapped chunks {len(overlapped_chunks)}")
    for i, chunks in enumerate(overlapped_chunks):
        chunked_data = joining_character.join(chunks)

        embeddings = generate_embeddings(openai_client, chunked_data)
        
        partition_key = get_config("PartitionKey")
        print(f"Saving chunk {i+1+total_already_uploaded} of {total_chunks}")
        create_document(cosmos_container, chunked_data, embeddings, i+total_already_uploaded, partition_key, "FinalRuling")

def main():
    try:
        opts, _ = getopt.getopt(sys.argv[1:], "rfdt:", ['upload-final-ruling', 'upload-fact-sheet', 'delete-document-type', 'document-type'])
    except getopt.GetoptError:
        print_help()
        sys.exit(2)
        
    if requesting_help(opts):
        print_help()
        sys.exit(0)        
    
    upload_ruling = get_flag(opts, '-r')
    if upload_ruling:
        upload_final_ruling()

    upload_fact = get_flag(opts, '-f')
    if upload_fact:
        upload_fact_sheet()

    delete_document = get_flag(opts, '-d')
    if delete_document:
        document_type = get_value(opts, '-t')
        delete_document_type(document_type)

def requesting_help(opts):
    help = next((o for o in opts if len(o) > 0 and o[0] == '-h'), None)
    return help != None

def print_help():
    print('You need help...')
    
def get_value(opts, parameter):
    value_arg = next((o for o in opts if len(o) > 0 and o[0] == parameter and len(o) == 2), None)
    return value_arg[1] if value_arg != None else None

def get_flag(opts, parameter):
    value_arg = next((o for o in opts if len(o) > 0 and o[0] == parameter), None)
    return value_arg != None

if __name__ == "__main__":
	sys.exit(main())