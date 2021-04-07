from datetime import timedelta
from itertools import chain
import json
import os
from pathlib import Path
import re
from shutil import copyfile
from timeit import default_timer as timer

import pandas as pd
from pdfminer.high_level import extract_text
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.pdftypes import PDFObjRef, resolve1
import matplotlib.pyplot as plt
import nltk
from nltk.corpus import stopwords
nltk.download('punkt')
nltk.download('stopwords')
import string
from wordcloud import WordCloud

DEBUG = True
INPUT_FOLDER_PATH = './input'
OUTPUT_FOLDER_PATH = './output'
OUTPUT_DIR_RENAMED_PDFS = 'renamed-pdfs'
GLOB_PATTERN_PDF = '**/*.pdf'
GLOB_PATTERN_XLSX = '**/*.xlsx'
GLOB_PATTERN_XLS = '**/*.xls'
GLOB_PATTERN_CSV = '**/*.csv'
SCIMAGO_RANKINGS_FILENAME = 'rankings-scimago.csv'
BLACKLIST_PARTIALS = ['cid:']
BLACKLIST_EXACT = ['author', 'pp', 'et', 'al', 'supply', 'chain', 'sustainability', 'sustainable', 'environmental', 'environment', 'management', 'research', 'literature', 'review', 'paper', 'journal']
BLACKLIST_PUNCTUATION = ['.', '-']
META_LABEL_PUB_YEAR = 'pub_year'
META_LABEL_TITLE = 'title'
NUM_FOLDER_SOURCE_PAIRS_TO_KEEP = 20


def _debug(message):
    if DEBUG:
        print(message)


def _get_sub_folders():
    """
    Returns a list of folder paths inside of the dedicated parent folder directory
    """
    folders_path = Path(INPUT_FOLDER_PATH)
    folders = [folder for folder in folders_path.iterdir() if folder.is_dir()]
    folders = sorted(folders, key=lambda f: f.name)
    num_pdfs = sum([len(list(folder.glob(GLOB_PATTERN_PDF))) for folder in folders])
    return folders, num_pdfs


def collect_metadata():
    """
    Builds output/metadata.json which contains some metadata for each PDF
    """
    metadata = {}
    folders , num_pdfs = _get_sub_folders()
    num_processed_pdfs = 0

    for folder in folders:
        pdfs = list(folder.glob(GLOB_PATTERN_PDF))
        
        for pdf in pdfs:
            num_processed_pdfs += 1
            metadata[pdf.name] = {}
            print()
            print(f'Collecting metadata {num_processed_pdfs}/{num_pdfs}: {pdf.name}')
            
            with open(pdf, 'rb') as fd:
                parser = PDFParser(fd)
                doc = PDFDocument(parser)
                if not doc.info:
                    pub_year = 'not available'
                    title = None
                else:
                    # Date
                    creation_date = doc.info[0]['CreationDate']
                    # Sometimes the date comes as a PDFObjRef
                    if isinstance(creation_date, PDFObjRef):
                        creation_date = resolve1(creation_date)
                    creation_date = creation_date.decode("utf-8")
                    pub_year = creation_date[2:6]
                    
                    # Title
                    title = doc.info[0].get('Title', b'')
                    # Sometimes the date comes as a PDFObjRef
                    if isinstance(title, PDFObjRef):
                        title = resolve1(title)
                    title = title.decode('unicode_escape') # Prevent exception from non-ascii chars
                    title = title.replace('\x00', '') # Remove null bytes which causes problems with file renaming
                    print(title)

                metadata[pdf.name][META_LABEL_PUB_YEAR] = pub_year
                metadata[pdf.name][META_LABEL_TITLE] = title
    
    # Write metadata file for all pdfs
    metadata_path = Path(f'{OUTPUT_FOLDER_PATH}/metadata.json')
    with open(metadata_path, 'w') as fd:
        json.dump(metadata, fd)


def _read_metadata():
    metadata_path = Path(f'{OUTPUT_FOLDER_PATH}/metadata.json')
    with open(metadata_path, 'r') as fd:
        metadata = json.load(fd)
    return metadata


def rename_files():
    """
    Often, downloaded pdfs come with a filename such as '1-s2.0-S036136821400004X-main'
    which makes navigation difficult when searching by paper title. 
    This function renames files to the title provided in the PDF metadata and copies them to a similar structure in output.
    """
    folders , num_pdfs = _get_sub_folders()
    metadata = _read_metadata()

    for folder in folders:
        pdfs = list(folder.glob(GLOB_PATTERN_PDF))
        # Create output dir
        output_dir = Path(OUTPUT_FOLDER_PATH, OUTPUT_DIR_RENAMED_PDFS, os.path.basename(folder))
        output_dir.mkdir(parents=True, exist_ok=True) 
        for pdf in pdfs:
            title = metadata.get(pdf.name, {}).get(META_LABEL_TITLE, None) or pdf.name
            # Convert to ACII chars for compatibility with Onedrive/Sharepoint
            title = str(title.encode('utf-8').decode('ascii', 'ignore'))
            # Filename compatibility for OneDrive/Sharepoint
            title = re.sub("[^ a-zA-Z1=0-9]+", "", title)
            # Reduce title length
            title = title[:70]
            title = f'{title}.pdf'
            copyfile(pdf, Path(output_dir, title))
            print(f'Copied and renamed \'{pdf.name}\' to {repr(title)}')   # Using repr to show hidden chars


def combine_search_files():
    folders , _ = _get_sub_folders()

    header_mappings = {
        'scopus': {
            'Source': 'Scopus',
            'Title': 'Title', 
            'Authors': 'Authors',
            'Year': 'Year', 
            'Journal': 'Source title', 
            'DOI': 'DOI',
            'URL': 'Link',
            'ISSN': None,
            'eISSN': None
        },
        'wos': {
            'Source': 'Web of Science',
            'Title': 'Article Title', 
            'Authors': 'Authors',
            'Year': 'Publication Year', 
            'Journal': 'Source Title', 
            'DOI': 'DOI',
            'URL': None,
            'ISSN': 'ISSN',
            'eISSN': 'EISSN'
        }, 
        'ieee': {
            'Source': 'IEEE',
            'Title': 'Document Title', 
            'Authors': 'Authors',
            'Year': 'Publication Year', 
            'Journal': 'Publication Title', 
            'DOI': 'DOI',
            'URL': 'PDF Link',
            'ISSN': 'ISSN',
            'eISSN': None
        },
        'springer': {
            'Source': 'Springer',
            'Title': 'Item Title', 
            'Authors': 'Authors',
            'Year': 'Publication Year', 
            'Journal': 'Publication Title', 
            'DOI': 'DOI',
            'URL': 'URL',
            'ISSN': None,
            'eISSN': None
        },
        'tf': {
            'Source': 'Taylor Francis',
            'Title': 'Article title', 
            'Authors': 'Authors',
            'Year': 'Volume year', 
            'Journal': 'Journal title', 
            'DOI': 'DOI',
            'URL': 'URL',
            'ISSN': None,
            'eISSN': None
        }
    }

    COLS_TO_READ = ['Folder', 'Source', 'Result Rank', 'Title', 'Authors', 'Year', 'Journal', 'ISSN', 'eISSN', 'DOI', 'URL']
    df_result = pd.DataFrame()
    df = pd.DataFrame()

    # Iterate XLSX, XLS, CSV files in folders
    for folder in folders:
        files = list(chain(*[list(folder.glob(pattern)) for pattern in [GLOB_PATTERN_XLSX, GLOB_PATTERN_XLS,GLOB_PATTERN_CSV]]))

        for f in files:
            # Remove extension
            source_type, file_type = f.name.split('.')
            # handles both cases if files are named `sks1-scopus` or just `scopus`
            source_type = source_type.split('-')[1] if '-' in source_type else source_type
                
            if file_type == 'csv':
                df = pd.read_csv(f)
            else:
                df = pd.read_excel(f)
  
            # Iterate columns. Some are special
            for col in COLS_TO_READ:
                if col == 'Result Rank':
                    df['Result Rank'] = df.index
                elif col == 'Folder':
                    df['Folder'] = folder.name
                else:
                    val = header_mappings[source_type][col]
                    if col == 'Source': 
                        df['Source'] = val
                    else:
                        try:
                            df[col] = df[[val]]
                        except:
                            print(f"{col} doesn't exist in {source_type}")

            # WoS has two ISSN columns
            if 'ISSN' in df.columns:
                if 'eISSN' in df.columns:
                    # https://stackoverflow.com/a/62681798/2016473
                    df['ISSN'] = df[['ISSN', 'eISSN']].stack().groupby(level=0).agg(','.join)
                df['ISSN'] = df['ISSN'].str.replace('-', '')

            df_result = pd.concat([df_result, df[df.columns.intersection(COLS_TO_READ)]])
    
    # Drop duplicates based on Title OR DOI, excluding null values
    size_before = df_result.shape[0]
    df_result = df_result[(~df_result['Title'].duplicated()) | df_result['Title'].isna()]
    df_result = df_result[(~df_result['DOI'].duplicated()) | df_result['DOI'].isna()]
    size_after = df_result.shape[0]
    print(f"Removed {size_before - size_after} duplicates from {size_before} records.")
    # Only keep top X results per folder-source pair
    df_result = df_result.groupby(['Folder', 'Source']).head(NUM_FOLDER_SOURCE_PAIRS_TO_KEEP)
    
    # Apply Journal Rankings
    df_rankings_scimago = pd.read_csv(Path(INPUT_FOLDER_PATH, SCIMAGO_RANKINGS_FILENAME), delimiter=';')
    df_rankings_scimago.rename({'SJR': 'Rank: SJR', 'Title': 'Journal'}, axis=1, inplace=True)
    # Merge on Journal name
    df_result = df_result.merge(df_rankings_scimago[['Journal', 'Rank: SJR']], on='Journal', how='left')
    # Merge on ISSN, could probably be simplified with pandas magic
    def _issn_lookup(series):
        issns = str(series[0])
        sjr = series[1] if not pd.isna(series[1]) else None
        if not sjr:
            for issn in issns.split(','):
                sjr = df_rankings_scimago.loc[df_rankings_scimago['Issn'].str.contains(issn), 'Rank: SJR'].tolist() or None
                if sjr:
                    if len(sjr) > 1:
                        _debug(f"Multiple ratings found for ISSN {issn}: {sjr}")
                    sjr = sjr[0]
                    break
        return sjr
    df_result[['Rank: SJR']] = df_result[['ISSN', 'Rank: SJR']].apply(lambda series: _issn_lookup(series), axis=1)

    # Reorder the columns
    COLS_TO_WRITE = ['Folder', 'Source', 'Title', 'Result Rank', 'Authors', 'Year', 'Journal', 'ISSN', 'Rank: SJR', 'DOI', 'URL']
    df_result = df_result[COLS_TO_WRITE]

    df_result.to_excel(Path(OUTPUT_FOLDER_PATH, 'combined_searches.xlsx'), index=False)


def analyze_text():
    folders , num_pdfs = _get_sub_folders()
    num_processed_pdfs = 0

    # For every Folder
    for folder in folders:
        pdfs = list(folder.glob(GLOB_PATTERN_PDF))
        corpus = []
        
        # For every PDF
        for pdf in pdfs:
            num_processed_pdfs += 1
            print()
            print(f'Analyzing text {num_processed_pdfs}/{num_pdfs}: {pdf.name}')

            # # For testing single PDFS
            # if '206049044.pdf' not in pdf.name:
            #     continue
            
            text = extract_text(pdf)

            # Remove blacklisted punctuation
            for p in BLACKLIST_PUNCTUATION:
                text = text.replace(p, '')

            # Make all text lowercase
            text = text.lower()

            # Preliminary check to see if we should run n^2 search later
            run_blacklist_partials = any(blp in text for blp in BLACKLIST_PARTIALS)

            # Tokenize
            word_list = nltk.word_tokenize(text)
            print(f'Words: {len(word_list)}')

            # Remove items with < 2 non-punctuation characters
            old_len_word_list = len(word_list)
            word_list = [word for word in word_list if len(word.translate(str.maketrans('', '', string.punctuation))) >= 2]
            print(f'Words removed with < 2 non-punctuation characters: {old_len_word_list - len(word_list)}')

            # Remove stop words
            stops = set(stopwords.words("english"))
            old_len_word_list = len(word_list)
            word_list = [word for word in word_list if word not in stops]
            print(f'Stop words removed: {old_len_word_list - len(word_list)}')

            # Remove numbers
            old_len_word_list = len(word_list)
            word_list = [word for word in word_list if not word.isnumeric()]
            print(f'Numbers removed: {old_len_word_list - len(word_list)}')

            # Manual partial removals
            if run_blacklist_partials:
                old_len_word_list = len(word_list)
                word_list = list(filter(lambda word: not any(blp in word for blp in BLACKLIST_PARTIALS), word_list))
                print(f'Blacklist partials removed: {old_len_word_list - len(word_list)}')
            
            # Manual exact removals
            old_len_word_list = len(word_list)
            word_list = [word for word in word_list if word not in BLACKLIST_EXACT]
            print(f'Blacklist exact removed: {old_len_word_list - len(word_list)}')

            corpus += word_list
        
        # Write corpus file for every folder
        corpus_path = Path(f'{OUTPUT_FOLDER_PATH}/corpus-{folder.name}.json')
        with open(corpus_path, 'w') as fd:
            json.dump(corpus, fd)


def create_wordcloud(corpus, filename):
    corpus_str =(" ").join(corpus)
    wordcloud = WordCloud(width = 1000, height = 500, background_color = 'white', include_numbers = True).generate(corpus_str)
    plt.figure(figsize=(15,8))
    plt.imshow(wordcloud)
    plt.axis("off")
    save_path = Path(f'{OUTPUT_FOLDER_PATH}/wordcloud-{filename}')
    plt.savefig(f'{save_path}.png', bbox_inches='tight')
    plt.close()


def create_wordclouds():
    combined_corpus = []
    for corpus_file in Path(OUTPUT_FOLDER_PATH).glob('corpus-*.json'):
        with open(corpus_file, 'r') as fd:
            corpus = json.load(fd)
        combined_corpus += corpus
        create_wordcloud(corpus, corpus_file.name.replace(".json", ""))
    create_wordcloud(corpus, 'combined')
        

def create_pub_year_plot():
    metadata = _read_metadata()
    counts = dict()
    for data in metadata.values():
        pub_year = data[META_LABEL_PUB_YEAR]
        if pub_year.isnumeric() and pub_year != '0000':
            counts[pub_year] = counts.get(pub_year, 0) + 1
        else:
            counts['N/A'] = counts.get('N/A', 0) + 1
    # Sort by year
    counts = dict(sorted(counts.items()))
    plt.figure(figsize=(15,8))
    plt.title('Number of Publications by Year')
    plt.xlabel('Year')
    plt.ylabel('Number of Publications')
    plt.bar(*zip(*counts.items()))
    save_path = Path(f'{OUTPUT_FOLDER_PATH}/pub_years')
    plt.savefig(f'{save_path}.png', bbox_inches='tight')
    plt.close()


def main():
    start = timer()
    # PDF to CSV
    # collect_metadata()
    # rename_files()
    # Combining CSVs
    combine_search_files()
    # Text Analysis
    # analyze_text()
    # create_wordclouds()
    # create_pub_year_plot()
    print(f'Elapsed Time: {timedelta(seconds=timer() - start)}')


if __name__ == '__main__':
    main()