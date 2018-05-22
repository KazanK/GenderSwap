# Imports the Google Cloud client library
from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types
import difflib
import inflect
import six
import re


f2m_dictionary = {
    "she" : "he",
    "shes" : "hes",
    "she's" : "he's",
    "herself" : "himself",
    "female" : "male",
    "woman" : "man",
    "lady" : "gentleman",
    "girl" : "boy",
    "sister" : "brother",
    "sis" : "bro",
    "daughter" : "son",
    "granddaughter" : "grandson",
    "lass" : "lad",
    "wife" : "husband",
    "bride" : "groom",
    "mother" : "father",
    "mother-in-law" : "father-in-law",
    "mom" : "dad",
    "mum" : "dad",
    "mommy" : "daddy",
    "aunt" : "uncle",
    "queen" : "king",
    "countess" : "count",
    "duchess" : "duke",
    "goddess" : "god",
    "princess" : "prince",
    "actress" : "actor",
    "giantess" : "giant",
    "headmistress" : "headmaster",
    "heiress" : "heir",
    "heroine" : "hero",
    "hostess" : "host",
    "huntress" : "hunter",
    "mistress" : "misteress",
    "waitress" : "waiter",
    "witch" : "wizard",
    "madam" : "sir",
    "ms" : "mr",
    "ms." : "mr.",

    "wolfess" : "wolf",
    "she-wolf" : "wolf",
    "shewolf" : "wolf",
    "vixen" : "fox",
    "lioness" : "lion",
    "tigress" : "tiger",
    "leopardess" : "leopard",
    "mare" : "stallion",
    "doe" : "buck",
    "sow" : "boar",
    "ewe" : "ram",

    "boob" : "moob",
    "breast" : "moob",
    "tit" : "moob",
    "pussy" : "hole",
    "vagina" : "hole"
}
special_cases = ['her', 'hers', 'ms', 'mrs', 'miss', 'misses']

# # part-of-speech tags from enums.PartOfSpeech.Tag
# pos_tags = ('UNKNOWN', 'ADJ', 'ADP', 'ADV', 'CONJ', 'DET', 'NOUN', 'NUM',
#             'PRON', 'PRT', 'PUNCT', 'VERB', 'X', 'AFFIX')
#
# # token tags from enums.DependencyEdge.Label
# labels = (  'UNKNOWN', 'ABBREV', 'ACOMP', 'ADVCL', 'ADVMOD', 'AMOD', 'APPOS',
#             'ATTR', 'AUX', 'AUXPASS', 'CC', 'CCOMP', 'CONJ', 'CSUBJ', 'CSUBJPASS',
#             'DEP', 'DET', 'DISCOURSE', 'DOBJ', 'EXPL', 'GOESWITH', 'IOBJ', 'MARK',
#             'MWE', 'MWV', 'NEG', 'NN', 'NPADVMOD', 'NSUBJ', 'NSUBJPASS', 'NUM',
#             'NUMBER', 'P', 'PARATAXIS', 'PARTMOD', 'PCOMP', 'POBJ', 'POSS',
#             'POSTNEG', 'PRECOMP', 'PRECONJ', 'PREDET', 'PREF', 'PREP', 'PRONL',
#             'PRT', 'PS', 'QUANTMOD', 'RCMOD', 'RCMODREL', 'RDROP', 'REF',
#             'REMNANT', 'REPARANDUM', 'ROOT', 'SNUM', 'SUFF', 'TMOD', 'TOPIC',
#             'VMOD', 'VOCATIVE', 'XCOMP', 'SUFFIX', 'TITLE', 'ADVPHMOD', 'AUXCAUS',
#             'AUXVV', 'DTMOD', 'FOREIGN', 'KW', 'LIST', 'NOMC', 'NOMCSUBJ',
#             'NOMCSUBJPASS', 'NUMC', 'COP', 'DISLOCATED', 'ASP', 'GMOD', 'GOBJ',
#             'INFMOD', 'MES', 'NCOMP')

"""
all tokens should be prepended with a space

EXCEPT for certain punctuation/special characters
, / \ ' ; : . ? ! @ ^ * - _ ~
or words following certain punctuation/special characters
/ \ ' @ - _
or numbers following certain punctuation/special characters
# $
or % when following a number

certain special characters should be prepended with a space
# $ & | = +

set characters require a stack to check `` '' "" () [] {} <>
opening characters should be be prepended with a space
closing characters should not
"""
# these characters should NOT  be prepended with a space
no_space_chars = (',', '/', '\\', ';', ':', '.', '?', '!', '@', '^', '*', '-', '_', '~')    # '\'',

# words (neither PUNCT nor NUM) following these characters should not be prepended with a space
no_space_words = ('/', '\\', '@', '-', '_') # '\'',

# numbers following these characters should not be prepended with a space
no_space_nums = ('#', '$')

# these characters SHOULD be prepended with a space
space_chars = ('#', '$', '&', '|', '=', '+')

# set characters need a stack to be dealt with
# opening characters should be be prepended with a space
# closing characters should not
quote_chars = ('`', '\'', '"')
opening_chars = ('(', '[', '{', '<')
closing_chars = (')', ']', '}', '>')


def analyze_syntax(text):
    """Detects syntax in the text."""
    if isinstance(text, six.binary_type):
        text = text.decode('utf-8')

    # Instantiate a plain text document.
    document = types.Document(
        content=text,
        type=enums.Document.Type.PLAIN_TEXT)

    # Detect syntax in the document
    return client.analyze_syntax(document).tokens


def f2m(tokens):
    full_text = []
    stack = []

    #for token in tokens:
    for i in range(0, len(tokens)):
        token = tokens[i]
        text = token.text.content
        # pos = pos_tags[token.part_of_speech.tag]
        # label = labels[token.dependency_edge.label]
        lower = text.lower()
        lemma = token.lemma.lower()
        pos = token.part_of_speech.tag
        plural = token.part_of_speech.number
        proper = token.part_of_speech.proper
        label = token.dependency_edge.label

        # Tokens to replace with male lemma
        if lemma in special_cases or lower in special_cases or lemma in f2m_dictionary:
            new_text = lower
            if lemma == 'her':
                if label == 37: #POSS
                    new_text = 'his'
                else:           #DOBJ = 18, IOBJ = 21, POBJ = 36, GOBJ = 79
                    new_text = 'him'
            elif lemma == 'hers':
                new_text = 'his'
            elif lower == 'ms':
                new_text = 'mr'
            elif lower == 'mrs':
                new_text = 'mr'
            elif lower in ['miss', 'misses']:
                if proper:
                    new_text = 'mister'
            elif lemma in f2m_dictionary:
                new_text = f2m_dictionary[lemma]
                if plural:      # If original text is plural, convert male lemma to plural too
                    new_text = inflect.engine().plural_noun(new_text)

            if text[0].isupper():                       # Retain original capitalization
                new_text = new_text.capitalize()

            if i == 0:                                  # If first token, append without spacing
                full_text.append(new_text)
            else:                                       # Append according to spacing rules
                append(full_text, stack, new_text, pos, tokens[i - 1])
        else:       # Just append the original text
            if i == 0:                                  # If first token, append without spacing
                full_text.append(text)
            else:                                       # Append according to spacing rules
                append(full_text, stack, text, pos, tokens[i - 1])

    return ''.join(full_text)


def append(full_text, stack, text, pos, prev_token):
    prev_text = prev_token.text.content
    prev_pos = prev_token.part_of_speech.tag

    if (text in no_space_chars) or \
            (prev_text in no_space_words and pos not in [7, 10]) or \
            (prev_text in no_space_nums and pos == 7) or \
            (text == '%' and prev_pos == 7):    # Special characters NOT prepended by a space
        full_text.append(text)
    elif text in space_chars:                   # Special characters prepended by a space
        full_text.append(' ' + text)
    elif text in quote_chars:                   # Quotation-like characters
        if text in stack:           # closing quote
            stack.pop()
            full_text.append(text)
        else:                       # opening quote
            stack.append(text)
            full_text.append(' ' + text)
    elif text in opening_chars:                 # Opening brackets
        stack.append(text)
        full_text.append(' ' + text)
    elif text in closing_chars:                 # Closing brackets
        stack.pop()
        full_text.append(text)
    elif prev_text in quote_chars:              # Tokens after quotation-like characters
        if prev_text in stack:      # following opening quote
            full_text.append(text)
        else:                       # following closing quote
            full_text.append(' ' + text)
    elif prev_text in opening_chars:            # Tokens after opening brackets
        full_text.append(text)
    elif prev_text in closing_chars:            # Tokens after closing brackets
        full_text.append(' ' + text)
    elif text.find('\'') != -1:                 # Contractions
        full_text.append(text)
    else:                                       # Everything else
        full_text.append(' ' + text)


def reconstruct(new, original):
    output = []
    seqm = difflib.SequenceMatcher(None, new, original, False)
    for opcode, a0, a1, b0, b1 in seqm.get_opcodes():
        delta_a = seqm.a[a0:a1]
        delta_b = seqm.b[b0:b1]
        newline = re.search(r'(\r|\n)+', delta_b)
        if opcode == 'equal':
            output.append(delta_a)
        elif opcode == 'insert' and newline:
            output.append(newline.group(0))
        elif opcode == 'delete':
            output.append(delta_a)
        elif opcode == 'replace':
            output.append(delta_a)
            if newline:
                output.append(newline.group(0))

    file = open('GenderSwap.txt', 'w')
    file.write(''.join(output))
    file.close()


# Instantiates a client
client = language.LanguageServiceClient()

# The text to analyze
#text = 'Her eyes were the most defining thing about her. She said, "Hi! What up fam; can you help me out, my \'dude\'?" She\'s up to something already-done I haven\'t seen before. She\'s pretty cool though. Those vixens have got spunk. That ball was hers.'
#text = 'yoooo "asdf (qwer) \'jkl <xcvb [uy]>\' {123}"'

# f1 = open('Test1.txt', 'r')
# text1 = f1.read()
# f1.close()
# split1 = text1.split(' ')
#
# f2 = open('Test2.txt', 'r')
# text2 = f2.read()
# f2.close()
# split2 = text2.split(' ')

#diff = difflib.ndiff(text1, text2)
#print(''.join(diff))

# text1 = 'hello\nworld\nfoo\nbar\nfizz\nbuzz'
# text2 = 'hello world foo bar fizz buzz'
# print('before:\n' + text2 + '\n')
# fixed = text2
# fixed = ''
# text1 = re.sub(r' *(\r|\n)+', ' \n\n', text1)

# j = 0
# for i, s in enumerate(difflib.ndiff(text2, text1)):
#     if s[0] == '-':
#         print(u'Delete "{}" from position {}'.format(s[-1], i))
#     elif s[0] == '+': #and s[-1] == '\n':
#         print(u'Add "{}" to position {}'.format(s[-1], i))
#
#         if s[-1] == '\n':
#             i = i - j
#             text2 = text2[:i] + '\n' + text2[i:]
#         else:
#             j = j + 1

f1 = open('Test.txt', 'r')
text = f1.read()
f1.close()

# Detects the syntax of the text
tokens = analyze_syntax(text)
swapped = f2m(tokens)
reconstruct(swapped, text)

print('Done')
