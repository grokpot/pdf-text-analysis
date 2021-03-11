from datetime import timedelta
import json
from pathlib import Path
from timeit import default_timer as timer

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

OUTPUT_PATH = 'output'
PDF_GLOB_PATTERN = '**/*.pdf'
BLACKLIST_PARTIALS = ['cid:']
BLACKLIST_EXACT = ['author', 'pp', 'et', 'al']
BLACKLIST_PUNCTUATION = ['.', '-']
PUB_YEAR_LABEL = 'pub_year'


def process_pdf_folders():
    metadata = {}
    
    pdf_folders_path = Path('./pdf-folders')
    folders = [folder for folder in pdf_folders_path.iterdir() if folder.is_dir()]
    num_pdfs = sum([len(list(folder.glob(PDF_GLOB_PATTERN))) for folder in folders])
    num_processed_pdfs = 1

    # For every Folder
    for folder in folders:
        pdfs = list(folder.glob(PDF_GLOB_PATTERN))
        corpus = []
        
        # For every PDF
        for pdf in pdfs:
            metadata[pdf.name] = {}

            print()
            print(f'Processing PDF {num_processed_pdfs}/{num_pdfs}: {pdf.name}')
            num_processed_pdfs += 1

            # # For testing single PDFS
            # if '206049044.pdf' not in pdf.name:
            #     continue

            # Collect Metadata
            with open(pdf, 'rb') as fd:
                parser = PDFParser(fd)
                doc = PDFDocument(parser)
                if not doc.info:
                    pub_year = 'not available'
                else:
                    creation_date = doc.info[0]['CreationDate']
                    # Sometimes the date comes as a PDFObjRef
                    if isinstance(creation_date, PDFObjRef):
                        creation_date = resolve1(creation_date)
                    creation_date = creation_date.decode("utf-8")
                    pub_year = creation_date[2:6]
                metadata[pdf.name][PUB_YEAR_LABEL] = pub_year
            
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
        corpus_path = Path(f'{OUTPUT_PATH}/corpus-{folder.name}.json')
        with open(corpus_path, 'w') as fd:
            json.dump(corpus, fd)

    # Write metadata file for all pdfs
    metadata_path = Path(f'{OUTPUT_PATH}/metadata.json')
    with open(metadata_path, 'w') as fd:
        json.dump(metadata, fd)


def create_wordcloud(corpus, filename):
    corpus_str =(" ").join(corpus)
    wordcloud = WordCloud(width = 1000, height = 500, background_color = 'white', include_numbers = True).generate(corpus_str)
    plt.figure(figsize=(15,8))
    plt.imshow(wordcloud)
    plt.axis("off")
    save_path = Path(f'{OUTPUT_PATH}/wordcloud-{filename}')
    plt.savefig(f'{save_path}.png', bbox_inches='tight')
    plt.close()


def create_wordclouds():
    combined_corpus = []
    for corpus_file in Path(OUTPUT_PATH).glob('corpus-*.json'):
        with open(corpus_file, 'r') as fd:
            corpus = json.load(fd)
        combined_corpus += corpus
        create_wordcloud(corpus, corpus_file.name.replace(".json", ""))
    create_wordcloud(corpus, 'combined')
        

def create_pub_year_plot():
    metadata_path = Path(f'{OUTPUT_PATH}/metadata.json')
    with open(metadata_path, 'r') as fd:
        metadata = json.load(fd)
    counts = dict()
    for data in metadata.values():
        pub_year = data[PUB_YEAR_LABEL]
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
    save_path = Path(f'{OUTPUT_PATH}/pub_years')
    plt.savefig(f'{save_path}.png', bbox_inches='tight')
    plt.close()


def main():
    start = timer()
    process_pdf_folders()
    create_wordclouds()
    create_pub_year_plot()
    print(f'Elapsed Time: {timedelta(seconds=timer() - start)}')



if __name__ == '__main__':
    main()