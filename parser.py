from os import path
import tarfile
import re
from copy import deepcopy
import json
from collections import OrderedDict


class tex_to_json:
    def __init__(self, tarname):
        self.text_counter = 0
        self.list_counter = 0
        self.footnote_counter = 0
        self.tarname = tarname
        self.document = {}

    def count_text(self):
        self.text_counter += 1
        return "%Text" + str(self.text_counter - 1)

    def count_list(self):
        self.list_counter += 1
        return "%List" + str(self.list_counter - 1)
    
    def count_footnote(self):
        self.footnote_counter += 1
        return str(self.footnote_counter - 1)

    def clean_text(self, text):
        if text.startswith("\n") or text.startswith(" "):
            return text[1:]
        else:
            return text

    def get_content_from_tar(self, filename):
        tar = tarfile.open(self.tarname)
        for member in tar.getmembers():
            if filename == member.name:
                f = tar.extractfile(member)
                return f.read().decode()

    def read_content_from_file(self, filename):
        content = self.get_content_from_tar(filename)
        inputs = re.findall("\\\input\{(\w*)\}", content)
        for inp in inputs:
            content = content.replace(
                "\input{" + inp + "}", self.read_content_from_file(inp + ".tex")
            )
        return content

    def find_main(self):
        tar = tarfile.open(self.tarname)
        docs = []
        for member in tar.getmembers():
            f = tar.extractfile(member)
            if f is not None:
                if ".tex" in member.name:
                    content = f.read()
                    if "\input" in str(content):
                        docs.append(member.name)

        candidates = deepcopy(docs)
        for filename in docs:
            content = self.get_content_from_tar(filename)
            for files in docs:
                if filename != files:
                    if "\input{" + files[:-4] + "}" in content:
                        if filename in candidates:
                            candidates.remove(files)

        if len(candidates) == 1:
            return candidates[0]

    def do_in_last_layer(self, d, function):
        """Accepts a dictionary and a function. 
        Then goes into the last layer of a dictionary and performs the function upon the entry. 
        With a special case for lists."""
        if isinstance(d, dict):
            for k, v in d.items():
                try:
                    d[k] = function(v)
                except:
                    if type(v) == list:
                        for idx, item in enumerate(v):
                            v[idx] = function(item)
                    self.do_in_last_layer(v, function)
        else:
            self.document["content"] = function(d)

    def find_part(self, regex, Text):
        output = OrderedDict()
        ex = re.compile(regex)
        result = re.finditer(ex, Text)
        for item in result:
            content = self.clean_text(item.groups()[2])
            if item.groups()[1] == None and content != "\n" and content != "":
                output[self.count_text()] = content
            elif item.groups()[1] != None:
                output[item.groups()[1]] = content
        if len(output) > 1:
            return output
        else:
            return Text

    def find_chapters(self, Text):
        return self.find_part("(?=(\\\chapter\{(.*?)\}((.|\\n)*?)(\\\chapter\{(.*?)\}|\\\\bibliographystyle)))",Text)

    def find_sections(self, Text):
        return self.find_part("(?=((?:\\\section\{(.*?)\}|^)((?:.|\\n)*?)(?:\\\section\{(?:.*?)\}|$)))",Text)

    def find_subsections(self, Text):
        return self.find_part("(?=((?:\\\subsection\{(.*?)\}|^)((?:.|\\n)*?)(?:\\\subsection\{(?:.*?)\}|$)))",Text)

    def find_subsubsections(self, Text):
        return self.find_part("(?=((?:\\\subsubsection\{(.*?)\}|^)((?:.|\\n)*?)(?:\\\subsubsection\{(?:.*?)\}|$)))",Text)

    def find_paragraphs(self, Text):
        return self.find_part("(?=((?:\\\paragraph\{(.*?)\}|^)((?:.|\\n)*?)(?:\\\paragraph\{(?:.*?)\}|$)))",Text)

    def find_lists(self, Text):
        output = OrderedDict()
        if Text.count("\\begin{itemize}") == 1:
            para = Text[: Text.find("\\begin{itemize}")]
            if para != "\\n":
                output[self.count_text()] = para
            para = Text[Text.find("\\end{itemize}") + 13 :]

            ex = re.compile("(?=(\\\\begin\{itemize\}((.|\\n)*?)\\\end\{itemize\}))")
            result = re.search(ex, Text)
            Text = result.groups()[0][15:]
            ex = re.compile("\\\item(.*)")
            result = re.findall(ex, Text)
            output[self.count_list()] = result
            if para != "\n" and para != "":
                output[self.count_text()] = para
            return output
        else:
            return Text

    def parse(self):
        content = self.read_content_from_file(self.find_main())
        start = False
        content= re.sub("\\\\textbf{(.*?)}",r"<b>\1</b>",content)
        content= re.sub("\\\\texttt{(.*?)}",r"<code>\1</code>",content)
        content= re.sub("\\\emph{(.*?)}",r"<i>\1</i>",content)
        content= re.sub("\\{\\\em (.*?)}",r"<em>\1</em>",content)
        content= re.sub("\\{\\\\bf (.*?)}",r"<b>\1</b>",content)
        content= re.sub("\\{\\\\tt (.*?)}",r"<code>\1</code>",content)
        content= re.sub("\\{\\\it (.*?)}",r"<i>\1</i>",content)
        content= re.sub("\\\\label{(.*?)}",r"<a name=\1></a>",content)
        content= re.sub("\\\\url{(.*?)}",r"<a href=\1>\1</a>",content)
        content= re.sub("~\\\\ref{(.*?)}",r"<a href=#\1>↩</a>",content)
        content= re.sub("\\\\ref{(.*?)}",r"<a href=ä\1>↩</a>",content)
        content= re.sub("%auto-ignore\\n",r"",content)
        content= re.sub("\\~\\\cite{.*?}",r"",content)
        content= re.sub("\\~\\\citet{.*?}",r"",content)
        content= re.sub("\\~\\\citep{.*?}",r"",content)
        content= re.sub("\\\cite{.*?}",r"",content)
        content= re.sub("\\\citet{.*?}",r"",content)
        content= re.sub("\\\citep{.*?}",r"",content)
        content = content.replace("\\quad","&nbsp;")
        content = content.replace("\\%","%")
        content = content.replace("\\#","#")
        content = content.replace("``","\"")
        content = content.replace("''","\"")
        output = ""
        self.document["title"] = re.findall("\\\\title\{(?:[^{}]*|\{(?:[^{}]*|\{[^{}]*\})*\})*\}", content)[0][7:-1]
        self.document["title"] = re.sub("\\\\","",self.document["title"])
        self.document["author"] = re.findall("\\\\author\{(?:[^{}]*|\{(?:[^{}]*|\{[^{}]*\})*\})*\}",content)[0][8:-1]
        self.document["author"] =  self.document["author"].replace("\And","<br/>")
        self.document["author"] =  self.document["author"].replace("\AND","<br/>")
        self.document["author"] =  self.document["author"].replace("\\\\","<br/>")
        self.document["author"] =  self.document["author"].replace("<br/><br/>","<br/>")
        self.document["author"] = re.sub("\\\\thanks\{(?:[^{}]*|\{(?:[^{}]*|\{[^{}]*\})*\})*\}","",self.document["author"])        
        for line in content.split("\n"):
            if start:
                if (
                    not line.startswith("%")
                    and "\maketitle" not in line
                    and "\include" not in line
                    and "\\vspace{" not in line
                    and "\\usepackage" not in line
                    and "\documentclass{" not in line
                    and "\\newcommand" not in line
                ):
                    output += line + "\n"

            if "\\begin{document}" in line:
                start = True
        abstract = output.split("\\begin{abstract}")[1].split("\end{abstract}")[0]
        output = output.split("\end{abstract}")[1]
        if abstract != "":
            self.document["abstract"] = self.clean_text(abstract)
        self.document["content"] = output
        while (
            self.document["content"].find("\n\n") != -1
            or self.document["content"].find("\n \n") != -1
        ):
            self.document["content"] = self.document["content"].replace("\n\n", "\n")
            self.document["content"] = self.document["content"].replace("\n \n", "\n")
        with open("test.txt", "w") as f:
            f.write(output)
        self.do_in_last_layer(self.document["content"], self.find_chapters)
        self.do_in_last_layer(self.document["content"], self.find_sections)
        self.do_in_last_layer(self.document["content"], self.find_subsections)
        self.do_in_last_layer(self.document["content"], self.find_subsubsections)
        self.do_in_last_layer(self.document["content"], self.find_paragraphs)
        self.do_in_last_layer(self.document["content"], self.find_lists)
        dump = json.dumps(self.document, indent=4)
        with open(self.tarname[:-7]+".json", "w") as json_file:
            json_file.write(dump)

parser = tex_to_json("test_new.tar.gz")
parser.parse()