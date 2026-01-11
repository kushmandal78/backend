import fitz
import hashlib
import json
import os
import pdfplumber
import PyPDF2
from PIL import Image 
import io
from pdf2docx import Converter
from pikepdf import Pdf
from pikepdf import Name


PDF_XIMAGE_OBJET_DIR = "pdfXobjet"
os.makedirs(PDF_XIMAGE_OBJET_DIR, exist_ok=True)

"""def save_unique_images_detailed(pdf_path):
    pdf = fitz.open(pdf_path)
    unique_images = {}
    
    for page_index in range(len(pdf)):
        page = pdf[page_index]
        image_list = page.get_images(full=True)  
        for img in image_list:            
            xref = img[0]
            base_image = pdf.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            
            # Create unique hash
            image_hash = hashlib.md5(image_bytes).hexdigest()
            
            if image_hash not in unique_images:
                # Content dictionary information
                content_info = {
                    'xref': img[0],        # XObject reference
                    'smask': img[1],       # Soft mask
                    'width': img[2],       # Width
                    'height': img[3],      # Height
                    'bpc': img[4],         # Bits per component
                    'colorspace': img[5],  # Color space
                    'alt_color': img[6],   # Alternate color
                    'name': img[7],        # Image name
                    'filter': img[8]       # Filter type
                }
                
                filename = f"pdfXobjet/{img[7]}.{image_ext}"
                
                # Save image
                with open(filename, "wb") as f:
                    f.write(image_bytes)
                
                unique_images = {
                    'filename': filename
                }
                
            else:
                print(f"⏩ DUPLICATE: {img[7]} (already saved)")

    pdf.close()
    return unique_images
 




def check_pdf_editable(file_path):
    try:
        # Method 1: Using PyPDF2
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            
            # If text is substantial, it's editable
            if len(text.strip()) > 50:  # Adjust threshold
                return True, "Editable PDF (contains selectable text)"
            else:
                return False, "Likely image-based PDF"
    except:
        return False, "Cannot process or encrypted PDF"
    



class PDFAnalyzer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.results = {
            'is_searchable': False,
            'confidence': 0,
            'text_volume': 0,
            'contains_images': False,
            'page_count': 0,
            'details': []
        }
    
    def analyze(self):
        # Method 1: Check with PyPDF2
        text_volume_pypdf = self._check_with_pypdf2()
        
        # Method 2: Check with PyMuPDF
        text_volume_fitz, images_count = self._check_with_fitz()
        
        # Method 3: Check with pdfplumber
        text_details = self._check_with_pdfplumber()
        
        # Combine results
        self.results['text_volume'] = max(text_volume_pypdf, text_volume_fitz)
        self.results['contains_images'] = images_count > 0
        
        # Decision logic
        total_chars = self.results['text_volume']
        self.results['page_count'] = len(text_details['pages'])
        
        if total_chars > 100:  # Adjust based on your needs
            self.results['is_searchable'] = True
            self.results['confidence'] = min(100, (total_chars / (self.results['page_count'] * 100)) * 100)
        else:
            self.results['is_searchable'] = False
            self.results['confidence'] = 100 if images_count > 0 else 50
            
        return self.results['confidence']
    
    def _check_with_pypdf2(self):
        try:
            with open(self.file_path, 'rb') as file:
                pdf = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf.pages:
                    text += page.extract_text()
                return len(text.strip())
        except:
            return 0
    
    def _check_with_fitz(self):
        doc = fitz.open(self.file_path)
        text_length = 0
        image_count = 0
        
        for page in doc:
            text_length += len(page.get_text().strip())
            image_count += len(page.get_images())
        
        doc.close()
        return text_length, image_count
    
    def _check_with_pdfplumber(self):
        result = {'pages': []}
        try:
            with pdfplumber.open(self.file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    result['pages'].append({
                        'text_length': len(text.strip()),
                        'words': len(text.split())
                    })
        except:
            pass
        return result

# Usag
#print(f"Searchable: {results['is_searchable']} ({results['confidence']:.1f}% confidence)")
"""
def remove_large_image_xobjects(input_pdf, output_pdf):
    """
    Remove large image XObjects from PDF pages.
    
    Args:
        input_pdf (str): Path to input PDF file
        output_pdf (str): Path to output PDF file
    
    Raises:
        Exception: If PDF cannot be opened or saved
    """
    try:
        pdf = Pdf.open(input_pdf)
        
        images_removed = 0
        for pno, page in enumerate(pdf.pages, start=1):
            for image_name, img_obj in list(page.images.items()):
                try:
                    if page.Resources and hasattr(page.Resources, 'XObject'):
                        if Name(image_name) in page.Resources.XObject:
                            del page.Resources.XObject[Name(image_name)]
                            images_removed += 1
                            print(f"Removed image {image_name} on page {pno}")
                except (KeyError, AttributeError) as e:
                    print(f"Warning: Could not remove image {image_name} on page {pno}: {e}")
                    continue
                except Exception as e:
                    print(f"Error processing image {image_name} on page {pno}: {e}")
                    continue
        
        pdf.save(output_pdf)
        print(f"Successfully processed PDF. Removed {images_removed} image(s).")
        
    except FileNotFoundError:
        raise Exception(f"Input PDF file not found: {input_pdf}")
    except Exception as e:
        raise Exception(f"Error processing PDF: {str(e)}")
    

    
    






    
  

