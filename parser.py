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
        self.tarname = tarname
        self.document = {}

    def count_text(self):
        self.text_counter += 1
        return "%Text" + str(self.text_counter - 1)

    def count_list(self):
        self.list_counter += 1
        return "%List" + str(self.list_counter - 1)

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

    def find_chapters(self, Text):
        output = OrderedDict()
        ex = re.compile(
            "(?=(\\\chapter\{(.*?)\}((.|\\n)*?)(\\\chapter\{(.*?)\}|\\\\bibliographystyle)))"
        )
        result = re.finditer(ex, Text)
        for item in result:
            output[item.groups()[6]] = item.groups()[3]
        if len(output) > 0:
            return output
        else:
            return Text

    def find_sections(self, Text):
        output = OrderedDict()
        ex = re.compile(
            "(?=((?:\\\section\{(.*?)\}|^)((?:.|\\n)*?)(?:\\\section\{(?:.*?)\}|$)))"
        )
        result = re.finditer(ex, Text)
        for item in result:
            if item.groups()[1] == None:
                output[self.count_text()] = item.groups()[2]
            else:
                output[item.groups()[1]] = item.groups()[2]
        if len(output) != 0:
            return output
        else:
            return Text

    def find_subsections(self, Text):
        output = OrderedDict()
        ex = re.compile(
            "(?=((?:\\\subsection\{(.*?)\}|^)((?:.|\\n)*?)(?:\\\subsection\{(?:.*?)\}|$)))"
        )
        result = re.finditer(ex, Text)
        for item in result:
            if item.groups()[1] != None:
                output[item.groups()[1]] = item.groups()[2]
        if len(output) != 0:
            return output
        else:
            return Text

    def find_subsubsections(self, Text):
        output = OrderedDict()
        ex = re.compile(
            "(?=((?:\\\subsubsection\{(.*?)\}|^)((?:.|\\n)*?)(?:\\\subsubsection\{(?:.*?)\}|$)))"
        )
        result = re.finditer(ex, Text)
        for item in result:
            if item.groups()[1] != None:
                output[item.groups()[1]] = item.groups()[2]
        if len(output) != 0:
            return output
        else:
            return Text


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
            if para != "\n":
                output[self.count_text()] = para
            return output
        else:
            return Text

    def parse(self):
        content = self.read_content_from_file(self.find_main())
        start = False
        output = ""
        self.document["title"] = re.findall("\\\\title\{(.*?)\}", content)[0]
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
            self.document["abstract"] = abstract
        self.document["content"] = output
        while self.document["content"].find("\n\n"):
            self.document["content"].replace("\n\n","\n")
        with open("test.txt", "w") as f:
            f.write(output)
        self.do_in_last_layer(self.document["content"], self.find_chapters)
        self.do_in_last_layer(self.document["content"], self.find_sections)
        self.do_in_last_layer(self.document["content"], self.find_subsections)
        self.do_in_last_layer(self.document["content"], self.find_subsubsections)
        self.do_in_last_layer(self.document["content"], self.find_lists)
        dump = json.dumps(self.document, indent=4)
        with open("test.json", "w") as json_file:
            json_file.write(dump)

