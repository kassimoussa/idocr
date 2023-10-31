from flask import Flask, request, jsonify 
import cx_Oracle
import pytesseract
import re
import cv2
import numpy as np
import json
import os
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "chrome-extension://giagjcgibhbgppolcpjdikcjhljelddi"}})


tessdata_dir_config = '--tessdata-dir "C:\\Program Files\\Tesseract-OCR\\tessdata"'
os.environ['TESSDATA_PREFIX'] = "C:\\Program Files\\Tesseract-OCR\\tessdata"
#os.environ['TESSDATA_PREFIX'] = '/usr/share/tesseract-ocr/4.00/tessdata/'


config = '--psm 4 --oem 3 -c textord_old_xheight=true textord_fix_xheight_bug=false preserve_interword_spaces=1 '
# Chemin vers l'exécutable Tesseract (modifier en fonction de votre configuration)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  

@app.route('/api/cin', methods=['POST'])
def process_image():
    try:
        # Get the uploaded image file
        image_file = request.files['image']
        
        # Convert the image file to OpenCV image format
        nparr = np.frombuffer(image_file.read(), np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Convert the image to grayscale
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply OCR using Tesseract
        text = pytesseract.image_to_string(gray_image, lang='fra', config=config)
        text = re.sub(r'[\u0600-\u06FF]', '', text)

       
        info_patterns = {
            'nom': r'[Nn]?[Oo][Mm]\s(.+?\s.+?\s.+?)\s',
            'date_naissance': r'[Nn][Éée]\s*[Ll]\s*[Ee]?\s+(\d{2})\.(\d{2})\.(\d{4})',
            'lieu_naissance': r'[Àà][Aa]?\s+(.*?)\s+',
            'nom_pere': r'\bde\b\s([A-Z][A-Z\s]+?[A-Z]\s[A-Z][A-Z\s]+?)\s',
            'nom_mere': r'[Ee][Tt]\s?[Dd][Ee]?\s?[a-z]?\s?(.+?\s.+?)\s',
            'profession': r'[Pp][Rr][Oo][A-Za-z]{7}\s+(.*?)\s+',
            'adresse': r'[Dd][Oo][Mm][Ii][Cc][Ii][A-Za-z]{2}\s+(.*?)\s+',
            'ncin': r'(\d{6})'
        }

        extracted_info = {}
        for key, pattern in info_patterns.items():
            match = re.search(pattern, text)
            if key == 'date_naissance':
                if match:
                    day, month, year = match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
                    extracted_info[key] = f'{day}/{month}/{year}'
                else:
                    extracted_info[key] = ''
            else:
                if match:
                    extracted_info[key] = match.group(1).strip()
                else:
                    extracted_info[key] = ''

        # Convertir le dictionnaire en format JSON
        json_output = json.dumps(extracted_info, ensure_ascii=False, indent=4)
 

        # Return the JSON response
        return json_output, 200
    except Exception as e:
        error_response = {'error': str(e)}
        return jsonify(error_response), 400


@app.route('/api/oldcni', methods=['POST'])
def process_oldcni():
    try:
        # Check if an image file is included in the request
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        # Get the uploaded image file
        image_file = request.files['image']
        
        # Convert the image file to OpenCV image format
        nparr = np.frombuffer(image_file.read(), np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Convertir l'image en niveaux de gris
        gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

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
        cropped_img = image[y:y+h, x:x+w]
        
        new_img_gray = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2GRAY)

        # Convert the image to grayscale
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply OCR using Tesseract
        text = pytesseract.image_to_string(new_img_gray, lang='fra', config=config)
        text = re.sub(r'[\u0600-\u06FF]', '', text)

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
            text_date_naissance = f'{day}-{month}-{year}' 
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
            #print(text_nom_mere)
            nom_mere_pattern2 = r'([A-Z]+ [A-Z]+)' 
            nom_mere_match2 = re.search(nom_mere_pattern2, text_nom_mere) 
            if nom_mere_match2:
                text_nom_mere2 = ' '.join(nom_mere_match2.groups())
                result["nom_mere"] = clean_text(text_nom_mere2)
            else:
                result["nom_mere"] = ''
        else:
            result["nom_mere"] = ''

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
            

        json_output = json.dumps(result, ensure_ascii=False, indent=4)
        #print(json_output)
 
        # Return the JSON response
        return json_output, 200
    except Exception as e:
        error_response = {'error': str(e)}
        return jsonify(error_response), 400


@app.route('/api/newcni', methods=['POST'])
def process_newcni():
    try:
        # Check if an image file is included in the request
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        # Get the uploaded image file
        image_file = request.files['image']
        
        # Convert the image file to OpenCV image format
        nparr = np.frombuffer(image_file.read(), np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Convertir l'image en niveaux de gris
        gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

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
        cropped_img = image[y:y+h, x:x+w]
        
        new_img_gray = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2GRAY)

        # Apply OCR using Tesseract
        text = pytesseract.image_to_string(new_img_gray, lang='fra', config=config)
        text = re.sub(r'[\u0600-\u06FF]', '', text)

       
        # Utilisation de regex pour extraire les informations
        nom_pattern = r"Nom\s+(.+)"
        domicile_pattern = r"Domicile Nom de la mère\s+(.+)"
        naissance_pattern = r"Date de Naissance Sexe\s+([\d-]+) ([MF])"
        emission_pattern = r"Date d'émission Date d'expiration\s+([\d-]+) ([\d-]+)"
        lieu_pattern = r"Lieu de Naissance\s+(.+)"
        profession_pattern = r"Profession\s+(.+)"
        CIN_pattern = r'(\d{9,10})'

        nom_match = re.search(nom_pattern, text)
        domicile_match = re.search(domicile_pattern, text)
        naissance_match = re.search(naissance_pattern, text)
        emission_match = re.search(emission_pattern, text)
        lieu_match = re.search(lieu_pattern, text)
        profession_match = re.search(profession_pattern, text)
        CIN_match = re.search(CIN_pattern, text)

        result = {}

        if nom_match:
            result["nom"] = nom_match.group(1)
        else:
            result["nom"] = ''

        if domicile_match:
            domicile_mere = domicile_match.group(1).split(' ')
            result["adresse"] = domicile_mere[0]
            result["nom_mere"] = domicile_mere[1] + ' ' + domicile_mere[2]
        else:
            result["adresse"] = '' 
            result["nom_mere"] = '' 

        if naissance_match:
            result["date_naissance"] = naissance_match.group(1)
            result["sexe"] = naissance_match.group(2)
        else:
            result["date_naissance"] = '' 
            result["sexe"] = '' 

        if emission_match:
            result["date_emission"] = emission_match.group(1)
            result["date_expiration"] = emission_match.group(2)
        else:
            result["date_emission"] = '' 
            result["date_expiration"] = '' 


        if lieu_match:
            result["lieu_naissance"] = lieu_match.group(1)
        else:
            result["lieu_naissance"] = ''

        if profession_match:
            result["profession"] = profession_match.group(1)
        else:
            result["profession"] = ''
        
        if CIN_match:
            result["ncni"] = CIN_match.group(1)
        else:
            result["ncni"] = ''

        json_output = json.dumps(result, ensure_ascii=False, indent=4)
        
        # Return the JSON response
        return json_output, 200
    except Exception as e:
        error_response = {'error': str(e)}
        return jsonify(error_response), 400


@app.route('/coucou', methods=['GET'])
def say_hello():
    return "Salut tout le monde"


# Oracle database connection details
oracle_host = "10.11.22.12"
oracle_port = 1521
oracle_service = "BSCSPROD.DJIBOUTITELECOM.DJ"
oracle_user = "SYSADM"
oracle_password = "SYSADM"
# Informations de connexion à la base de données Oracle
dsn_tns = cx_Oracle.makedsn(oracle_host, oracle_port, service_name=oracle_service) 

@app.route('/api/insert', methods=['POST'])
def insert_data():
    try:

        # Récupérer les données du formulaire
        dir_num = request.form['dir_num']
        sms_text = request.form['sms_text']

        # Connexion à la base de données
        connection = cx_Oracle.connect(user=oracle_user, password=oracle_password, dsn=dsn_tns)
        cursor = connection.cursor()

        # Requête d'insertion avec une sous-requête pour obtenir la nouvelle valeur de FP_SMS_REQUEST_ID
        insert_query = """
            INSERT INTO SYSADM.FP_SMS_INTERFACE 
            (FP_SMS_REQUEST_ID, PRIORITY, DIR_NUM, NPCODE, NP_SHDES, SMS_TEXT, ENTRY_DATE, STATUS) 
            VALUES 
            ((SELECT NVL(MAX(FP_SMS_REQUEST_ID), 0) + 1 FROM FP_SMS_INTERFACE), 1, :dir_num, 1, 'E.164', :sms_text, SYSDATE, NULL)
        """

        # Exécution de la requête d'insertion
        cursor.execute(insert_query, {'dir_num': dir_num, 'sms_text': sms_text})

        # Validation de la transaction
        connection.commit()

        # Fermeture du curseur et de la connexion
        cursor.close()
        connection.close()

        return jsonify({'message': 'Insertion réussie.'}), 200

    except Exception as e:
        # En cas d'erreur, annulation de la transaction
        connection.rollback()
        cursor.close()
        connection.close()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':

    # Apply the ProxyFix middleware
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)


    app.run(debug=True,)

