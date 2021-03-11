import json
from pathlib import Path

from pdfminer import high_level
import matplotlib.pyplot as plt
import nltk
from nltk.corpus import stopwords
nltk.download('punkt')
nltk.download('stopwords')
import string
from wordcloud import WordCloud

CORPUS_FILENAME = 'corpus.json'

def write_word_lists():
    folder_path = Path('./pdfs')
    pdfs = list(folder_path.glob('**/*.pdf'))
    corpus = []
    
    for pdf in pdfs:
        print()
        print(pdf)
        text = high_level.extract_text(pdf)

        # Make all text lowercase
        text = text.lower()

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
        word_list = [word for word in word_list if not word.isnumeric()]

        # Manual removals
        blacklist = ['author', 'pp',]
        word_list = [word for word in word_list if word not in blacklist]

        corpus += word_list
    
    with open(CORPUS_FILENAME, 'w') as fd:
        json.dump(corpus, fd)


def process_word_lists():
    with open(CORPUS_FILENAME, 'r') as fd:
        corpus = json.load(fd)

    corpus_str =(" ").join(corpus)
    wordcloud = WordCloud(width = 1000, height = 500, background_color = 'white', include_numbers = True).generate(corpus_str)
    plt.figure(figsize=(15,8))
    plt.imshow(wordcloud)
    plt.axis("off")
    plt.savefig("your_file_name"+".png", bbox_inches='tight')
    plt.show()
    plt.close()

def main():
    write_word_lists()
    process_word_lists()



if __name__ == '__main__':
    main()