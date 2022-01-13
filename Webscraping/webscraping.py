from bs4 import BeautifulSoup
import requests
import csv
import time
import pandas as pd

def get_page_url(nr):
    return str('https://www.finn.no/realestate/homes/search.html?page=' + str(nr) + '&sort=PUBLISHED_DESC')

def column_in_header(csv_file,row,header):
    with open(csv_file, 'r+') as f:
        d_writer = csv.DictWriter(f, fieldnames = header)
        reader = csv.reader(f)
        lengde = len(list(reader))
        for key in row.keys():
            if key != None:
                if key not in header:
                    header.append(key)
        if lengde == 0:
            d_writer.writeheader() 
        return header

def append_to_csv(row, header):
    csv_file = 'Finn_boligTEST.csv'
    with open(csv_file,'a') as f:
        thewriter = csv.DictWriter(f, fieldnames=header)
        column_in_header(csv_file, row, header)
        thewriter.writerow(row)
        return header

def make_int(string):
    tall = ''
    for char in string:
        if char in '0123456789-':
            tall +=(char)
    if '-' in tall:
        tall = tall.split('-')
        tall = (float(tall[0])+float(tall[-1]))/2
    else:
        try:
            tall = int(tall)
            tall = round(tall)
        except ValueError as error:
            print('FEILKODE', tall)
    return tall

def kvm_pris_convert(kvm_pris):
    kvm_pris = kvm_pris.split('m²')
    if len(kvm_pris)>0:
        kvm = make_int(kvm_pris[0])
        pris = make_int(kvm_pris[-1])
    else:
        pris = None
        kvm = None
    return kvm, pris

def scrape_finn():

    antall = 1
    header = ['Boligtype', 'Eieform bolig', 'Soverom', 'Primærrom', 'Bruksareal', 'Etasje', 'Byggeår', 'Energimerking', 'Pris', 'URL', 'ID', 'Nybygg', 'Enhetsid', 'Solforhold', 'Utendørsareal', 'Tomteareal', 'Bruttoareal', 'Rom', 'Ant etasjer', 'Tomt', 'Renovert år', 'Areal', 'Boligselgerforsikring', 'Grunnflate', 'Festeavgift'] #Liste med header-navn



    for i in range(50):
        i+=1 #Starter på page 1 (ikke 0)
        html_mainpage = requests.get(get_page_url(i)).text
        soup_mainpage = BeautifulSoup(html_mainpage,'lxml')
        boligliste = soup_mainpage.find_all('article', class_ = 'ads__unit')
        for j in range(len(boligliste)):
            bolig_info = {}
            html_bolig = boligliste[j].find('a', class_ = 'ads__unit__link')

            #URL
            url = str(html_bolig['href'])
            if j==0:
                url = 'https://www.finn.no' + url

            

            id = html_bolig['id']
            kvm_pris = boligliste[j].find('div', class_ = 'ads__unit__content__keys').text
            kvm, pris  = kvm_pris_convert(kvm_pris)

            soup_bolig = BeautifulSoup(requests.get(url).text,'lxml')
            if 'https://www.finn.no/eiendom/nybygg' in url:
                info_list_class = 'definition-list definition-list--inline'
            else:
                info_list_class = 'definition-list definition-list--cols1to2'
            
            info_liste = soup_bolig.find('dl', class_ = info_list_class)
            if info_liste != None:
                info_liste = info_liste.text.split('\n')
                info_liste_clean = []
                for el in info_liste:
                    if el != None:
                        if el.replace(' ','')!='':
                            if el == 'Eieform':
                                el = 'Eieform bolig'
                            info_liste_clean.append(el)
            if (len(info_liste_clean)%2!=0):
                info_liste_clean.append('ERROR')
            
            keys_m2_mean = ['Primærrom','Bruksareal','Areal','Tomteareal','Grunnflate','Bruttoareal','Soverom','Festeavgift']

            for k in range(0,len(info_liste_clean),2):
                key = info_liste_clean[k].strip()
                value = info_liste_clean[k+1].strip()
                if key in keys_m2_mean:
                    value = make_int(value) #Fjerner m² fra bestemte keys
                bolig_info[key] = value

            bolig_info['Pris'] = pris
            bolig_info['URL'] = url
            bolig_info['ID'] = id    

            if 'https://www.finn.no/eiendom/nybygg' in url:
                bolig_info['Nybygg'] = 1
                bolig_info['Primærrom'] = kvm
                bolig_info['Energimerking'] = None
                bolig_info['Byggeår'] = 2021
                
            else:
                bolig_info['Nybygg'] = 0
            

            #for key, value in bolig_info.items(): hbwekfuhwiuf
                #print(f'{key} = {value}')

            header = append_to_csv(bolig_info, header) #Oppdaterer header til True
            
            if antall%10==0:
                print('Appended row nr: ', antall)
            if antall%50==0:
                print('########## Appended site nr: ', i,  '##########')
            antall += 1

            
scrape_finn()

# Endring

    
        