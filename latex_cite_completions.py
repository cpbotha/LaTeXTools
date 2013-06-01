import sublime, sublime_plugin
import os, os.path
import re
import getTeXRoot

def match(rex, str):
    m = rex.match(str)
    if m:
        return m.group(0)
    else:
        return None

# recursively search all linked tex files to find all
# included bibliography tags in the document and extract
# the absolute filepaths of the bib files
def find_bib_files(rootdir, src, bibfiles):
    if src[-4:].lower() != ".tex":
        src = src + ".tex"

    file_path = os.path.normpath(os.path.join(rootdir,src))
    print "Searching file: " + repr(file_path)
    # See latex_ref_completion.py for why the following is wrong:
    #dir_name = os.path.dirname(file_path)

    # read src file and extract all bibliography tags
    try:
        src_file = open(file_path, "r")
    except IOError:
        sublime.status_message("LaTeXTools WARNING: cannot open included file " + file_path)
        print "WARNING! I can't find it! Check your \\include's and \\input's." 
        return

    src_content = re.sub("%.*","",src_file.read())
    bibtags =  re.findall(r'\\bibliography\{[^\}]+\}', src_content)

    # extract absolute filepath for each bib file
    for tag in bibtags:
        bfiles = re.search(r'\{([^\}]+)', tag).group(1).split(',')
        for bf in bfiles:
            if bf[-4:].lower() != '.bib':
                bf = bf + '.bib'
            # We join with rootdir - everything is off the dir of the master file
            bf = os.path.normpath(os.path.join(rootdir,bf))
            bibfiles.append(bf)

    # search through input tex files recursively
    for f in re.findall(r'\\(?:input|include)\{[^\}]+\}',src_content):
        input_f = re.search(r'\{([^\}]+)', f).group(1)
        find_bib_files(rootdir, input_f, bibfiles)

# Based on html_completions.py
# see also latex_ref_completions.py
#
# It expands citations; activated by 
# cite<tab>
# citep<tab> and friends
#
# Furthermore, you can "pre-filter" the completions: e.g. use
#
# cite_sec
#
# to select all citation keywords starting with "sec". 
#
# There is only one problem: if you have a keyword "sec:intro", for instance,
# doing "cite_intro:" will find it correctly, but when you insert it, this will be done
# right after the ":", so the "cite_intro:" won't go away. The problem is that ":" is a
# word boundary. Then again, TextMate has similar limitations :-)
#
# There is also another problem: * is also a word boundary :-( So, use e.g. citeX if
# what you want is \cite*{...}; the plugin handles the substitution

class LatexCiteCompletionsDEPRECATED(sublime_plugin.EventListener):

    def on_query_completions(self, view, prefix, locations):
        # Only trigger within LaTeX
        if not view.match_selector(locations[0],
                "text.tex.latex"):
            return []

        # Get the contents of line 0, from the beginning of the line to
        # the current point
        l = locations[0]
        line = view.substr(sublime.Region(view.line(l).a, l))
            

        # Reverse, to simulate having the regex
        # match backwards (cool trick jps btw!)
        line = line[::-1]
        #print line

        # Check the first location looks like a ref, but backward
        # NOTE: use lazy match for the fancy cite part!!!
        # NOTE2: restrict what to match for fancy cite
        rex = re.compile("([^_]*_)?([a-zX]*?)etic")
        expr = match(rex, line)
        #print expr
        
        # See first if we have a cite_ trigger
        if expr:
            # Return the completions
            prefix, fancy_cite = rex.match(expr).groups()
            preformatted = False
            post_brace = "}"
            if prefix:
                prefix = prefix[::-1] # reverse
                if prefix[0]=='_':
                    prefix = prefix[1:] # chop off if there was a _
            else:
                prefix = "" # because this could be a None, not ""
            if fancy_cite:
                fancy_cite = fancy_cite[::-1]
                # fancy_cite = fancy_cite[1:] # no need to chop off?
                if fancy_cite[-1] == "X":
                    fancy_cite = fancy_cite[:-1] + "*"
            else:
                fancy_cite = "" # just in case it's a None
            print prefix, fancy_cite

        # Otherwise, see if we have a preformatted \cite{}
        else:
            rex = re.compile(r"([^{}]*)\{?([a-zX*]*?)etic\\")
            expr = match(rex, line)

            if not expr:
                return []

            preformatted = True
            post_brace = ""
            prefix, fancy_cite = rex.match(expr).groups()
            if prefix:
                prefix = prefix[::-1]
            else:
                prefix = ""
            if fancy_cite:
                fancy_cite = fancy_cite[::-1]
                if fancy_cite[-1] == "X":
                    fancy_cite = fancy_cite[:-1] + "*"
            else:
                fancy_cite = ""
            print prefix, fancy_cite

        # Reverse back expr
        expr = expr[::-1]

        if not preformatted:
            # Replace cite expression with "C" to save space in drop-down menu
            expr_region = sublime.Region(l-len(expr),l)
            #print expr, view.substr(expr_region)
            ed = view.begin_edit()
            expr = "\cite" + fancy_cite + "{" + prefix
            view.replace(ed, expr_region, expr)
            view.end_edit(ed)
        

        completions = ["TEST"]

        #### GET COMPLETIONS HERE #####
        root = getTeXRoot.get_tex_root(view)

        print "TEX root: " + repr(root)
        bib_files = []
        find_bib_files(os.path.dirname(root),root,bib_files)
        # remove duplicate bib files
        bib_files = list(set(bib_files))
        print "Bib files found: ",
        print repr(bib_files)

        if not bib_files:
            print "Error!"
            return []
        bib_files = ([x.strip() for x in bib_files])
        
        print "Files:"
        print repr(bib_files)
         
        completions = []
        
        kp = re.compile(r'@[^\{]+\{(.+),')
        # new and improved regex
        # we must have "title" then "=", possibly with spaces
        # then either {, maybe repeated twice, or "
        # then spaces and finally the title
        # We capture till the end of the line as maybe entry is broken over several lines
        # and in the end we MAY but need not have }'s and "s
        tp = re.compile(r'\btitle\s*=\s*(?:\{+|")\s*(.+)', re.IGNORECASE)  # note no comma!
        kp2 = re.compile(r'([^\t]+)\t*')

        for bibfname in bib_files:
            # # THIS IS NO LONGER NEEDED as find_bib_files() takes care of it
            # if bibfname[-4:] != ".bib":
            #     bibfname = bibfname + ".bib"
            # texfiledir = os.path.dirname(view.file_name())
            # # fix from Tobias Schmidt to allow for absolute paths
            # bibfname = os.path.normpath(os.path.join(texfiledir, bibfname))
            # print repr(bibfname) 
            try:
                bibf = open(bibfname)
            except IOError:
                print "Cannot open bibliography file %s !" % (bibfname,)
                sublime.status_message("Cannot open bibliography file %s !" % (bibfname,))
                continue
            else:
                bib = bibf.readlines()
                bibf.close()
            print "%s has %s lines" % (repr(bibfname), len(bib))
            # note Unicode trickery
            keywords = [kp.search(line).group(1).decode('ascii','ignore') for line in bib if line[0] == '@']
            titles = [tp.search(line).group(1).decode('ascii','ignore') for line in bib if tp.search(line)]
            if len(keywords) != len(titles):
                print "Bibliography " + repr(bibfname) + " is broken!"
            # Filter out }'s and ,'s at the end. Ugly!
            nobraces = re.compile(r'\s*,*\}*(.+)')
            titles = [nobraces.search(t[::-1]).group(1)[::-1] for t in titles]
            completions += zip(keywords, titles)


        #### END COMPLETIONS HERE ####

        print "Found %d completions" % (len(completions),)

        if prefix:
            completions = [comp for comp in completions if prefix.lower() in "%s %s" % (comp[0].lower(),comp[1].lower())]

        # popup is 40chars wide...
        t_end = 80 - len(expr)
        r = [(prefix + " "+title[:t_end], keyword + post_brace) 
                        for (keyword, title) in completions]

        print "%d bib entries matching %s" % (len(r), prefix)

        # def on_done(i):
        #     print "latex_cite_completion called with index %d" % (i,)
        #     print "selected" + r[i][1]

        # print view.window()

        return r


class LatexCiteCommand(sublime_plugin.TextCommand):

    # Remember that this gets passed an edit object
    def run(self, edit):
        # get view and location of first selection, which we expect to be just the cursor position
        view = self.view
        point = view.sel()[0].b
        print point
        # Only trigger within LaTeX
        # Note using score_selector rather than match_selector
        if not view.score_selector(point,
                "text.tex.latex"):
            return

        # Get the contents of the current line, from the beginning of the line to
        # the current point
        line = view.substr(sublime.Region(view.line(point).a, point))
        print line
            

        # Reverse, to simulate having the regex
        # match backwards (cool trick jps btw!)
        line = line[::-1]
        #print line

        # Check the first location looks like a cite_, but backward
        # NOTE: use lazy match for the fancy cite part!!!
        # NOTE2: restrict what to match for fancy cite
        rex = re.compile("([^_]*_)?([a-zX]*?)etic")
        expr = match(rex, line)

        # See first if we have a cite_ trigger
        if expr:
            # Return the completions
            prefix, fancy_cite = rex.match(expr).groups()
            preformatted = False
            post_brace = "}"
            if prefix:
                prefix = prefix[::-1] # reverse
                prefix = prefix[1:] # chop off 
            else:
                prefix = "" # just in case it's None, though here
                            # it shouldn't happen!
            if fancy_cite:
                fancy_cite = fancy_cite[::-1]
                # fancy_cite = fancy_cite[1:] # no need to chop off?
                if fancy_cite[-1] == "X":
                    fancy_cite = fancy_cite[:-1] + "*"
            else:
                fancy_cite = "" # again just in case
            print prefix, fancy_cite

        # Otherwise, see if we have a preformatted \cite{}
        else:
            # we also search for the case where the user has multiple refs
            # separated by commas. (cpbotha)
            rex = re.compile(r"([^{},]*)(,?[^{}]*)\{?([a-zX*]*?)etic\\")
            expr = match(rex, line)

            if not expr:
                return []

            preformatted = True
            post_brace = ""
            # \citeFC{existing,prefix}
            prefix, existing_keys, fancy_cite = rex.match(expr).groups()
            if prefix:
                prefix = prefix[::-1]
            else:
                prefix = ""

            if fancy_cite:
                fancy_cite = fancy_cite[::-1]
                if fancy_cite[-1] == "X":
                    fancy_cite = fancy_cite[:-1] + "*"
            else:
                fancy_cite = ""
            print prefix, fancy_cite
        # Reverse back expr
        expr = expr[::-1]

        #### GET COMPLETIONS HERE #####

        root = getTeXRoot.get_tex_root(view)

        print "TEX root: " + repr(root)
        bib_files = []
        find_bib_files(os.path.dirname(root),root,bib_files)
        # remove duplicate bib files
        bib_files = list(set(bib_files))
        print "Bib files found: ",
        print repr(bib_files)

        if not bib_files:
            sublime.error_message("No bib files found!") # here we can!
            return []
        bib_files = ([x.strip() for x in bib_files])
        
        print "Files:"
        print repr(bib_files)
        
        completions = []

        # cpbotha:
        # note that capturing nested structures with regexp is not done:
        # http://stackoverflow.com/a/3558943/532513
        # either we'll have to write a parser, or stick to regexps and
        # live with the issues.

        # cpbotha: there may be spaces between { and keyword
        kp = re.compile(r'@[^\{]+\{\s*(.+),')
        # new and improved regex
        # we must have "title" then "=", possibly with spaces
        # then either {, maybe repeated twice, or "
        # then spaces and finally the title
        # We capture till the end of the line as maybe entry is broken over several lines
        # and in the end we MAY but need not have }'s and "s
        tp = re.compile(r'\btitle\s*=\s*(?:\{+|")\s*(.+)', re.IGNORECASE)  # note no comma!
        # Tentatively do the same for author
        ap = re.compile(r'\bauthor\s*=\s*(?:\{+|")\s*(.+)', re.IGNORECASE)

        for bibfname in bib_files:
            try:
                bibf = open(bibfname)
            except IOError:
                print "Cannot open bibliography file %s !" % (bibfname,)
                sublime.status_message("Cannot open bibliography file %s !" % (bibfname,))
                continue
            else:
                bib = bibf.readlines()
                bibf.close()
            print "%s has %s lines" % (repr(bibfname), len(bib))


            #################################################################
            # new and improved cpbotha bibtex parser begins here
            # * old parser used separate regexps for keywords, authors and 
            #   titles. would break when entries were commented out by 
            #   removing @ (common practice), and in cases where record 
            #   had no title (user mistake)
            # * old parser would also break with @string{lala = 'value'} 
            #   constructs.
            # * new parser is (slightly) more intelligent about catching 
            #   complete record, and hence does not get tripped up by above 
            #   problems.
            # * todo: support for multiline titles and authors (old parser 
            #   also did not support this)

            keywords = []
            titles = []
            authors = []
            curkeyword = ""
            curtitle = ""
            curauthors = ""

            def add_record():
                # new citekey, store previous one if we have all desired 
                # fields
                if curkeyword and curtitle and curauthors:
                    keywords.append(curkeyword)
                    titles.append(curtitle)
                    authors.append(curauthors)


            for line in bib:
                mo = kp.search(line)
                if mo:
                    add_record()

                    # reset
                    curkeyword = mo.group(1).decode('ascii','ignore')
                    curtitle = ""
                    curauthors = ""

                else:
                    # current line is not a new @type{citekey,
                    # so let's see if it's a title or an authors line

                    # if we don't have a title yet, see
                    if not curtitle:
                        mo = tp.search(line)
                        if mo:
                            curtitle = mo.group(1).decode('ascii','ignore')

                    if not curauthors:
                        mo = ap.search(line)
                        if mo:
                            curauthors = mo.group(1).decode('ascii','ignore')

            # if we have a valid keyword, title and authors
            # add it to the lists
            add_record()

            # new cpbotha parser ends here
            #################################################################

            print "Found %d total bib entries" % (len(keywords),)

            # Filter out }'s and ,'s at the end. Ugly!
            nobraces = re.compile(r'\s*,*\}*(.+)')
            titles = [nobraces.search(t[::-1]).group(1)[::-1] for t in titles]
            authors = [nobraces.search(a[::-1]).group(1)[::-1] for a in authors]
            completions += zip(keywords, titles, authors)

        #### END COMPLETIONS HERE ####

        # filter against keyword, title, or author
        if prefix:
            completions = [comp for comp in completions if prefix.lower() in "%s %s %s" \
                                                    % (comp[0].lower(),comp[1].lower(), comp[2].lower())]

        # Note we now generate citation on the fly. Less copying of vectors! Win!
        def on_done(i):
            print "latex_cite_completion called with index %d" % (i,)
            
            # Allow user to cancel
            if i<0:
                return

            if preformatted:
                last_brace = ""
                ek = existing_keys[::-1]

            else:
                last_brace = "}"
                ek = ""

            cite = "\\cite" + fancy_cite + "{" + ek + completions[i][0] + last_brace

            print "selected %s:%s by %s" % completions[i] 
            # Replace cite expression with citation
            expr_region = sublime.Region(point-len(expr),point)
            ed = view.begin_edit()
            view.replace(ed, expr_region, cite)
            view.end_edit(ed)

        
        view.window().show_quick_panel([[title + " (" + keyword+ ")", author] \
                                        for (keyword,title, author) in completions], on_done)
 

