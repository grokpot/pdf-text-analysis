# pdf-text-analysis
This tool is used for text processing and analysis of multiple folders of multiple PDF files.
It assumes you have the following structure:
```
pdf-folders
    folder-1
        PDF-1
        PDF-2
        PDF-3
        ...
    folder-2
        PDF-4
        PDF-5
        PDF-6
        ...
    ...
```

The tool can be run simply by `pip install -r requirements.txt` and then `python3 runner.py`.  

The tool processes the PDFs, applies text processing per specified rules (via global vars at the top of the file), and outputs wordclouds for each folder, as well as one for the combined corpus of text.  

In addition, a bar chart of the publication dates is output.
