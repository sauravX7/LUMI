import os
from PIL import Image
import pytesseract
import pymupdf  # fitz
from io import BytesIO

from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Import components we already have
from backend.database import embedding_function
from backend.brain import general_llm # Use the same LLM

# --- State Management ---
# This will hold our in-memory RAG chain for the *current* document
CURRENT_DOC_CHAIN = None
# ---

def extract_text_from_file(file_path):
    """Extracts text from PDF or Image using OCR."""
    print(f"Processor: Extracting text from {file_path}")
    text = ""
    
    if file_path.lower().endswith('.pdf'):
        doc = pymupdf.open(file_path)
        for page_num, page in enumerate(doc):
            # 1. First, try to get simple text
            text += page.get_text()
            
            # 2. Then, get images and OCR them (for scanned PDFs)
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                try:
                    pil_image = Image.open(BytesIO(image_bytes))
                    text += pytesseract.image_to_string(pil_image)
                    print(f"  ... OCR'd image from page {page_num + 1}")
                except Exception as e:
                    print(f"Error processing image on page {page_num + 1}: {e}")
        doc.close()
        
    elif file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        try:
            pil_image = Image.open(file_path)
            text = pytesseract.image_to_string(pil_image)
            print("  ... OCR'd standalone image")
        except Exception as e:
            print(f"Error processing image {file_path}: {e}")
            
    else:
        return "Unsupported file type."
        
    return text

def load_and_process_document(file_path: str) -> str:
    """Loads, processes, and sets a document as the active RAG chain."""
    global CURRENT_DOC_CHAIN
    
    try:
        # 1. Extract Text (with OCR)
        raw_text = extract_text_from_file(file_path)
        if not raw_text or raw_text == "Unsupported file type.":
            CURRENT_DOC_CHAIN = None
            return f"Error: Unsupported file or no text found."
        
        # 2. Split Text
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=200
        )
        chunks = text_splitter.split_text(raw_text)
        
        if not chunks:
            CURRENT_DOC_CHAIN = None
            return "Error: Could not split text from document."

        # 3. Create In-Memory Vector Store
        print(f"Processor: Creating in-memory vector store for {len(chunks)} chunks...")
        vector_store = FAISS.from_texts(
            texts=chunks, 
            embedding=embedding_function
        )
        retriever = vector_store.as_retriever()
        
        # 4. Create RAG Chain
        template = """
        Answer the question based *only* on the following context from the document:
        {context}
        Question: {question}
        Answer:
        """
        prompt = PromptTemplate.from_template(template)
        
        CURRENT_DOC_CHAIN = (
            {"context": retriever, "question": RunnablePassthrough()}
            | prompt
            | general_llm # Reusing the general_llm from brain
            | StrOutputParser()
        )
        
        print("Processor: Document is loaded and ready for questions.")
        return f"Successfully loaded {os.path.basename(file_path)}. Ready for questions."
        
    except Exception as e:
        print(f"Error in load_and_process_document: {e}")
        CURRENT_DOC_CHAIN = None
        return "An error occurred during document processing."

def ask_document_question(user_input: str) -> str:
    """Asks a question to the currently loaded document chain."""
    print("Processor: Received question for document.")
    if CURRENT_DOC_CHAIN is None:
        return "Please upload a document before asking questions about it."
        
    try:
        response = CURRENT_DOC_CHAIN.invoke(user_input)
        return response
    except Exception as e:
        print(f"Error in ask_document_question: {e}")
        return "I encountered an error trying to answer that question."