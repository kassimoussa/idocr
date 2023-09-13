import pytesseract
import re
import cv2
import json
import os


# Prompt the user for the image name
img_name = input("Enter the image filename (e.g., 06.jpg): ")

# Check if the entered file exists
if not os.path.isfile(img_name):
    print(f"The file '{img_name}' does not exist.")
    exit(1)

# Load the image
img = cv2.imread(img_name)

# Convertir l'image en niveaux de gris
gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Appliquer un flou gaussien pour réduire le bruit
blurred_img = cv2.GaussianBlur(gray_img, (13, 13), 0)

# Appliquer un seuil pour binariser l'image
_, threshold_img = cv2.threshold(blurred_img, 60, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

# Trouver les contours dans l'image binarisée
contours, _ = cv2.findContours(threshold_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Trouver le contour le plus grand (probablement la carte d'identité)
largest_contour = max(contours, key=cv2.contourArea)

# Obtenir les coordonnées du rectangle englobant du plus grand contour
x, y, w, h = cv2.boundingRect(largest_contour)

# Rogner l'image d'origine en utilisant les coordonnées du rectangle
cropped_img = img[y:y+h, x:x+w]
 
new_img_gray = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2GRAY)

# Apply OCR using Tesseract 
#pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Set the TESSDATA_PREFIX environment variable
os.environ['TESSDATA_PREFIX'] = '/usr/share/tesseract-ocr/4.00/tessdata/'
tessdata_dir_config = '--tessdata-dir "C:\\Program Files\\Tesseract-OCR\\tessdata"'
config = '--psm 4 --oem 3 -c textord_old_xheight=true textord_fix_xheight_bug=false preserve_interword_spaces=1 ' 

text = pytesseract.image_to_string(new_img_gray, lang='fra', config = config)
#text = re.sub(r'[\u0600-\u06FF]', '', text) 

# Function to clean extracted text
def clean_text(texte):
    cleaned_text = re.sub(r'[^a-zA-Z0-9\s]', '', texte)  # Remove non-alphanumeric characters
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)  # Replace multiple spaces with a single space
    return cleaned_text.strip()  # Remove leading and trailing spaces

def clean_spaces(texte):
    new_text = re.sub(r'\s+', ' ', texte)
    return new_text.strip() 


# Utilisation de regex pour extraire les informations
nom_pattern = r'[Nn]?[Oo][Mm]\s+(.+)' 
date_naissance_pattern = r'(\d{2})\.(\d{2})\.(\d{4})'
lieu_naissance_pattern = r'[Àà][Aa]?\s+(.*?)\s+'
adresse_pattern = r'[Dd][Oo][Mm][A-Za-z\.]{2,}\s+(.*?)\s+'
nom_pere_pattern = r'[d][e]\s+(.+)'
nom_mere_pattern = r'[e][t]\s?[d][e]\s+(.+)'
profession_pattern = r'[Pp][Rr][Oo][A-Za-z]{7}\s+(.*?)\s+'
ncni_pattern = r'(\d{6})'

nom_match = re.search(nom_pattern, text)
date_naissance_match = re.search(date_naissance_pattern, text)
lieu_naissance_match = re.search(lieu_naissance_pattern, text)
adresse_match = re.search(adresse_pattern, text)
nom_pere_match = re.search(nom_pere_pattern, text)
nom_mere_match = re.search(nom_mere_pattern, text)
profession_match = re.search(profession_pattern, text)
ncni_match = re.search(ncni_pattern, text)

result = {}

if nom_match:
    text_nom = ' '.join(nom_match.groups()) 
    #print(text_nom)
    new_nom_pattern = r'([A-Z]+)\s+([A-Z]+)\s+([A-Z]+)'
    text_nom_match = re.search(new_nom_pattern, text_nom)
    new_text_nom = ' '.join(text_nom_match.groups()) 
    #print(new_text_nom2)
    result["nom"] = new_text_nom
else:
    result["nom"] = ''
    
if date_naissance_match:
    day, month, year = date_naissance_match.group(1).strip(), date_naissance_match.group(2).strip(), date_naissance_match.group(3).strip()
    text_date_naissance = f'{day}/{month}/{year}' 
    #print(text_date_naissance)
    result["date_naissance"] = text_date_naissance
else:
    result["date_naissance"] = ''
    
date_pattern = r'(\d{2}\.\d{2}\.\d{4})'
# Search for the date pattern in the extracted text
date_match = re.search(date_pattern, text)
if date_match:
    ddd = date_match.group(1)

if date_match:
    # Get the position where the date pattern ends
    date_end_position = date_match.end()

    # Find the start and end positions of the line after the date
    line_start_position = text.find('\n', date_end_position) + 1
    line_end_position = text.find('\n', line_start_position)

    # Extract the line after the date
    line_below_date = text[line_start_position:line_end_position].strip() 
    line_below_date = clean_spaces(line_below_date) 
    #print(line_below_date)
    
    # Use regular expression to capture uppercase sequences (including characters after /)
    uppercase_sequence_match = re.search(r'([A-Z/-]{4,})', line_below_date)
    # r'(?<![a-z])[A-Z\/\-. ]{3,}(?![a-z])'
    

    if uppercase_sequence_match:
        lieu_naissance = uppercase_sequence_match.group(1)
        #print(lieu_naissance)
        result["lieu_naissance"] = lieu_naissance
    else:
        # If not found in the current line, try in the line below
        next_line_start_position = text.find('\n', line_end_position) + 1
        next_line_end_position = text.find('\n', next_line_start_position)

        if next_line_start_position != -1 and next_line_end_position != -1:
            next_line = text[next_line_start_position:next_line_end_position].strip()

            # Use regular expression to capture uppercase sequences (including characters after /)
            
            uppercase_sequence_match = re.search(r'([A-Z/-]{4,})', next_line)

            if uppercase_sequence_match:
                lieu_naissance = uppercase_sequence_match.group(1)
                #print(lieu_naissance)
                result["lieu_naissance"] = lieu_naissance
            else:
                result["lieu_naissance"] = ''
                
#if lieu_naissance_match: 
#    text_lieu_naissance = ' '.join(lieu_naissance_match.groups()) 
#    print(text_lieu_naissance)
    
if adresse_match: 
    text_adresse = adresse_match.group(1) 
    #print(text_adresse)
    result["adresse"] = text_adresse
else:
    result["adresse"] = ''
    
if nom_pere_match: 
    text_nom_pere = ' '.join(nom_pere_match.groups()) 
    #print(text_nom_pere)
    nom_pere_pattern2 = r'([A-Z]+ [A-Z]+)'
    nom_pere_match2 = re.search(nom_pere_pattern2, text_nom_pere)
    if nom_pere_match2:
        text_nom_pere2 = ' '.join(nom_pere_match2.groups()) 
        result["nom_pere"] = clean_text(text_nom_pere2)
    else:
        result["nom_pere"] = ''
else:
    result["nom_pere"] = ''
    
if nom_mere_match: 
    text_nom_mere = ' '.join(nom_mere_match.groups()) 
    print(text_nom_mere)
    nom_mere_pattern2 = r'([A-Z]+ [A-Z]+)'
    nm2 = clean_text(text_nom_mere)
    nom_mere_match2 = re.search(nom_mere_pattern2, text_nom_mere)
    print(nm2)
    if nom_mere_match2:
        text_nom_mere2 = ' '.join(nom_mere_match2.groups()) 
        result["nom_mere"] = clean_text(text_nom_mere2)
    else:
        result["nom_mere"] = ''
else:
    result["nom_mere"] = 'nome_mere : not found'
    
if profession_match: 
    text_profession = ' '.join(profession_match.groups()) 
    #print(text_profession)   
    result["profession"] = text_profession
else:
    result["profession"] = ''
    
if ncni_match: 
    text_ncni = ' '.join(ncni_match.groups()) 
    #print(text_ncni)
    result["ncni"] = text_ncni
else:
    result["ncni"] = ''
    

json_result = json.dumps(result, ensure_ascii=False, indent=4)
print(json_result)
#print("#####################")

print(text)

