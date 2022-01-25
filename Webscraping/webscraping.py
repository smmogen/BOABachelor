from bs4 import BeautifulSoup
import requests
import csv
import time
import datetime
import pandas as pd
import random as r
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

date_today = datetime.date.today() #Dagens dato (global variable)

def get_page_url(nr, fylke):
    #Henter url for fylker-nummer
    if fylke=='fylkenummer':
        return str('https://www.finn.no/realestate/homes/search.html?page=' + str(nr) + '&sort=PUBLISHED_DESC')
    #Lager url med fylke og sidenummer (1-50)
    return str('https://www.finn.no/realestate/homes/search.html?location=0.'+ str(fylke) +'&page=' + str(nr) + '&sort=PUBLISHED_DESC')
    
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

def remove_rows(row,header):
    new_dict={}
    for key,value in row.items():
        if key in header:
            new_dict[key]=value
    return new_dict

def append_to_csv(row, header, csv_file):
    row = remove_rows(row,header) #Fjerner ting som ikke skal med
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
        except:
            a=0
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

def number_of_ads(fylker): #Tar inn fylker som en dictionary
    html_mainpage = requests.get(get_page_url(1, 'fylkenummer')).text #Henter html for finn-mainpage
    soup_mainpage = BeautifulSoup(html_mainpage,'lxml')
    fylkenum = (soup_mainpage.find_all('ul', class_ = 'list')) #Finner alle <ul> på mainpage

    for fylke, liste in fylker.items():
        for li in fylkenum: #Går gjennom alle <li> for å finne fylke-li
            index_num = str(li).find(fylke) #Ser om aktuelt fylke finnes i <li>
            if index_num != -1: #Går inn hvis man får treff på <li>
                fylke_lengde = len(fylke) #Finner lengden på fylke-navn
                start = (index_num+fylke_lengde+39)
                fylke_antall='' #Oppretter tom string for å legge til siffer
                for char in str(li)[start:start+6]:
                    if char in '0123456789':
                        fylke_antall+=char
                fylke_antall = (int(fylke_antall)) #Gjør om til int
                liste.append(fylke_antall) #Legger til i fylker-dictionary

def number_of_pages(antall_annonser):
        antall_sider = (antall_annonser//50) #Finner antall sider det er annonser for
        if antall_sider*50<antall_annonser:
            antall_sider +=1 #Legger til siste side
        if antall_sider>50:
            print('Max antall sider: 50')
            antall_sider=50 #Begrenser antall sider til 50
        return antall_sider

def make_dict(liste, fasit):
    dictionary={}
    for el in fasit:
        if el in liste:
            dictionary[el]=1
        else:
            dictionary[el]=0
    return dictionary

def find_adress(adresse):
    nom = Nominatim(user_agent='Andyyy')
    geocode = RateLimiter(nom.geocode, min_delay_seconds=2.5, error_wait_seconds=5.0,max_retries=2)
    time.sleep(1) #Hindrer forhåpentligvis å bli kastet ut av serveren

    adresse_format = geocode(adresse)
    adresse_dict = {} #Oppretter to dict til adresse
    
    if adresse_format!=None:
        adresse_dict['Latitude']=adresse_format.latitude
        adresse_dict['Longitude']=adresse_format.longitude
        addresse_liste = adresse_format.address.split(',') #Splitter opp adressen for å hente ut spesifikk info
        adresse_dict['Land']=addresse_liste[-1] #Land
        adresse_dict['Postnummer']=make_int(addresse_liste[-2]) #Postnummer
        adresse_dict['Kommune']=addresse_liste[-4] #Kommune
    return adresse_dict

def format_date(dato_string):
    dato_string = dato_string.split('.')
    if len(dato_string)>=3:
        dag = dato_string[0].strip()
        måned = dato_string[1].strip()
        år = dato_string[2][0:5].strip()

        #Gjør om måned fra string til int
        måned_dict = {'jan':'01','feb':'02','mar':'03','apr':'04','mai':'05','jun':'06','jul':'07','aug':'08','sep':'09','okt':'10','nov':'11','des':'12'}
        for måned_str, måned_int in måned_dict.items():
            if måned==måned_str:
                måned=måned_int
        
        #Sjekker at dag er 2 siffer
        if len(dag)==1:
            dag = '0'+dag
        
        #Lager iso-format på datoen
        dato_isoformat = datetime.date.fromisoformat(år+'-'+måned+'-'+dag)

        return (date_today-dato_isoformat) #Returnerer antall dager siden annonsen
    else:
        return 0

def add_info(bolig_info, soup_bolig, info_list_class, fasteliteter, header):
    #Legger til info fra standard-liste
    info_liste = soup_bolig.find('dl', class_ = info_list_class)
    info_liste_clean = []
    if info_liste != None:
        info_liste = info_liste.text.split('\n')
        for el in info_liste:
            if el != None:
                if el.replace(' ','')!='':
                    if el == 'Eieform':
                        el = 'Eieform bolig'
                    info_liste_clean.append(el)

    #Legger til info fra ekstra-liste
    extra_liste = soup_bolig.find_all('dl', class_ = 'definition-list')
    for liste in extra_liste:
        if liste != None:
            liste = liste.text.split('\n')
            # extra_liste_clean = []
            for el in liste:
                if el != None:
                    if el.replace(' ','')!='':
                        if el == 'Eieform':
                            el = 'Eieform bolig'
                        info_liste_clean.append(el)
                        
    
    #Legger til info fra "Fastiliteter"-listen
    fastiliteter_liste_html = soup_bolig.find_all('ul', class_ = 'list list--bullets list--cols1to2 u-mb16')
    fastiliteter_liste = [] #Oppretter tom liste
    for punkt in fastiliteter_liste_html:
        if punkt != None:
            punkt = punkt.text.split('\n')
            for el in punkt:
                if el != None:
                    if el.replace(' ','')!='':
                        fastiliteter_liste.append(el) #Legger til fasteliteter i listen
    
    #Gjør om til en dictionary for fasteliteter
    fasteliteter_dict = make_dict(fastiliteter_liste, fasteliteter)

    #Legger til adresse, postnummer, kommune, latitude, longitude
    adresse = soup_bolig.find('p', class_ = 'u-caption')
    #if adresse==None:
     #   adresse = soup_bolig.find_All('p', class_ = 'inline-block')
    if adresse!=None:
        adresse_dict = find_adress(adresse.text) #Får en dict med diverse info fra adressen
        bolig_info.update(adresse_dict) #Legger til adresse-info i bolig_info

    #Sjekker hvor mange dager annonsen har ligget på finn
    antall_dager_finn = soup_bolig.findAll('td', class_ = 'u-no-break u-pl8')
    if antall_dager_finn!=[]: #Sjekker at man har hentet info fra finn
        dager_siden = format_date(antall_dager_finn[-1].text) #Antall dager siden annonsen
    else:
        dager_siden=0
    bolig_info['Dager siden annonse']=dager_siden #Legger til i bolig_info

    #Sjekker at listen er partall
    if (len(info_liste_clean)%2!=0):
        info_liste_clean.append('ERROR')

    #Rydder i diverse m² formateringer og gjør om til int
    keys_m2_mean = ['Primærrom','Bruksareal','Areal','Tomteareal','Grunnflate','Bruttoareal','Soverom','Festeavgift', 'Omkostninger', 'Totalpris','Kommunale avg.','Formuesverdi']

    for k in range(0,len(info_liste_clean),2):
        key = info_liste_clean[k].strip()
        value = info_liste_clean[k+1].strip()
        if key in keys_m2_mean:
            value = make_int(value) #Fjerner m² fra bestemte keys
        bolig_info[key] = value #Legger til key/value i bolig_info

    #Legger til fasteliteter i bolig_info    
    bolig_info.update(fasteliteter_dict)

def tidsinfo(antall_annonser,antall_annonser_fylke,fylke, i):
    print()
    tid_nå = datetime.datetime.now().strftime("%H:%M:%S")
    soving = r.randint(10,30)
    tid_igjen = round((antall_annonser-antall_annonser_fylke)/60, 2) #Beregner tid igjen
    print(f'Klokkeslett: {tid_nå}')
    print()
    print(f'########## Appended site nr: {i}/{antall_annonser//50} ##########')
    print(f"Pauser i {soving} sekund for å hindre å bli kastet ut av serveren")
    print(f"Estimert tid igjen for {fylke} (1 sekund pr annonse): {tid_igjen} minutter")
    print(f"Annonser hentet: {antall_annonser_fylke}/{antall_annonser}")
    time.sleep(soving) #10-30 sek sleep

def scrape_finn():

    filnavn = input('Filnavn: ')
    filnavn +=".csv" #Legger til csv-ending på filen
    antall = 0 #Antall rader

    header = ['Pris', 'Boligtype', 'Eieform bolig', 'Soverom', 'Primærrom', 'Bruksareal', 'Etasje', 'Byggeår', 'Energimerking', 'URL', 'ID', 'Dager siden annonse', 'Nybygg', 'Land', 'Fylke', 'Postnummer', 'Kommune', 'Latitude', 'Longitude', 'Omkostninger', 'Totalpris','Kommunale avg.','Formuesverdi', 'Tomteareal','Aircondition', 'Alarm','Balkong/Terrasse','Takterasse','Barnevennlig','Bredbåndstilknytning','Fellesvaskeri','Garasje/P-plass','Heis','Ingen gjenboerer','Kabel-TV','Lademulighet','Livsløpsstandard','Moderne','Offentlig vann/kloakk','Parkett','Peis/Ildsted','Rolig','Sentralt','Utsikt','Vaktmester-/vektertjeneste','Bademulighet','Fiskemulighet','Turterreng'] #Liste med header-navn + fasteliteter

    fasteliteter = ['Aircondition', 'Alarm','Balkong/Terrasse','Takterasse','Barnevennlig','Bredbåndstilknytning','Fellesvaskeri','Garasje/P-plass','Heis','Ingen gjenboerer','Kabel-TV','Lademulighet','Livsløpsstandard','Moderne','Offentlig vann/kloakk','Parkett','Peis/Ildsted','Rolig','Sentralt','Utsikt','Vaktmester-/vektertjeneste','Bademulighet','Fiskemulighet','Turterreng'] #Liste med fasteliteter som finnes på finn.no

    fylker = {'Agder':[22042], 'Innlandet':[22034], 'Møre og Romsdal':[20015], 'Nordland':[20018], 'Oslo':[20061], 'Rogaland':[20012], 'Troms og Finnmark':[22054], 'Trøndelag':[20016], 'Vestfold og Telemark':[22038], 'Vestland':[22046],'Viken':[22030]} #Fylker med tilhørende finn-kode (url) som liste

    number_of_ads(fylker) #Legger til antall annonser i fylker-dictionaryen. {Fylke-navn:[finn-kode,antall annonser]}

    for fylke, fylke_nummer in fylker.items(): #Går gjennom alle fylkene
        finn_kode = fylke_nummer[0]
        antall_annonser = fylke_nummer[1]
        antall_sider = number_of_pages(antall_annonser) #Henter antall sider for hvert fylke
        print(f'Antall sider for {fylke} er {antall_sider}')
        antall_annonser_fylke = 0 #Resettes for hvert fylke

        for i in range(1,antall_sider): #Går gjennom opptil 50 sider for hvert fylke
            html_mainpage = requests.get(get_page_url(i, finn_kode)).text
            soup_mainpage = BeautifulSoup(html_mainpage,'lxml')
            boligliste = soup_mainpage.find_all('article', class_ = 'ads__unit')

            for j in range(len(boligliste)): #Går inn på hver enkelt artikkel på siden
                bolig_info = {}
                html_bolig = boligliste[j].find('a', class_ = 'ads__unit__link')

                #Url for hver enkelt artikkel
                url = str(html_bolig['href'])
                if j==0:
                    url = 'https://www.finn.no' + url

                id = html_bolig['id']
                kvm_pris = boligliste[j].find('div', class_ = 'ads__unit__content__keys').text
                kvm, pris  = kvm_pris_convert(kvm_pris)

                #Henter ut masse info fra html
                soup_bolig = BeautifulSoup(requests.get(url).text,'lxml')

                #Forskjellig URL alt etter om det er nybygg eller brukt
                if 'https://www.finn.no/eiendom/nybygg' in url:
                    info_list_class = 'definition-list definition-list--inline'
                else:
                    info_list_class = 'definition-list definition-list--cols1to2'

                #Legger til info i dictionary
                add_info(bolig_info, soup_bolig, info_list_class, fasteliteter, header)

                bolig_info['Pris'] = pris
                bolig_info['URL'] = url
                bolig_info['ID'] = id 
                bolig_info['Fylke'] = fylke  

                if 'https://www.finn.no/eiendom/nybygg' in url:
                    bolig_info['Nybygg'] = 1
                    bolig_info['Primærrom'] = kvm
                    bolig_info['Energimerking'] = None
                    bolig_info['Byggeår'] = 2021
                    
                else:
                    bolig_info['Nybygg'] = 0

                header = append_to_csv(bolig_info, header, filnavn) #Oppdaterer header til True
                
                if antall%10==0:
                    print(f'Appended row nr: {antall}. Fylke: {fylke}')
                    time.sleep(3)
                if antall%50==0: #Statistikk
                    tidsinfo(antall_annonser,antall_annonser_fylke,fylke, i) #Print diverse nyttig info

                #Sjekker antall annonser
                if antall_annonser_fylke==antall_annonser:
                    print(f"Antall annonser for {fylke}: {antall_annonser_fylke}")
                antall += 1
                antall_annonser_fylke +=1
        
scrape_finn() 