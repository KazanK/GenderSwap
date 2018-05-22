# Imports the Google Cloud client library
from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types
import difflib
import inflect
import six
import re


# Dictionary of female to male nouns/pronouns
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

# Special cases for female to male swaps that need to be handled separately
f2m_specials = ['her', 'hers', 'ms', 'mrs', 'miss', 'misses']

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
    """Detects syntax in the text.

    :param text: Text to analyze
    :return: List of tokens from GCP NLP
    """

    if isinstance(text, six.binary_type):
        text = text.decode('utf-8')

    # Instantiate a plain text document.
    document = types.Document(
        content=text,
        type=enums.Document.Type.PLAIN_TEXT)

    # Detect syntax in the document
    return client.analyze_syntax(document).tokens


def f2m(tokens):
    """Swaps female nouns/pronouns with male equivalents.

    :param tokens: List of tokens from GCP NLP
    :return: String with all detected female nouns/pronouns swapped. Text from tokens are joined back together with
    proper spacing, but line breaks are lost.
    """
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
        plural = token.part_of_speech.number > 1
        proper = token.part_of_speech.proper
        label = token.dependency_edge.label

        # Tokens to replace with male lemma
        if lower in f2m_specials or lemma in f2m_dictionary:
            new_text = ''

            if lower == 'hers':
                new_text = 'his'
            elif lower == 'her':
                if label == 37: #POSS
                    new_text = 'his'
                else:           #DOBJ = 18, IOBJ = 21, POBJ = 36, GOBJ = 79
                    new_text = 'him'
            elif lower == 'ms':
                new_text = 'mr'
            elif lower == 'mrs':
                new_text = 'mr'
            elif lower in ['miss', 'misses']:
                if proper:
                    new_text = 'mister'
                else:
                    new_text = lower
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


def append(full_text, stack, add_text, pos, prev_token):
    """Appends a new string to full_text, whose contents are be joined back together in f2m(), while handling spacing
    for special characters.

    :param full_text: List of strings that are ready to be joined into the final text
    :param stack: Stack used to check for open/close set characters `` '' "" () [] {} <>
    :param add_text: Text to be appended from the current Token
    :param pos: Part of speech of add_text
    :param prev_token: Previous Token
    :return: None
    """

    prev_text = prev_token.text.content
    prev_pos = prev_token.part_of_speech.tag

    if (add_text in no_space_chars) or \
            (prev_text in no_space_words and pos not in [7, 10]) or \
            (prev_text in no_space_nums and pos == 7) or \
            (add_text == '%' and prev_pos == 7):    # Special characters NOT prepended by a space
        full_text.append(add_text)
    elif add_text in space_chars:                   # Special characters prepended by a space
        full_text.append(' ' + add_text)
    elif add_text in quote_chars:                   # Quotation-like characters
        if add_text in stack:           # closing quote
            stack.pop()
            full_text.append(add_text)
        else:                       # opening quote
            stack.append(add_text)
            full_text.append(' ' + add_text)
    elif add_text in opening_chars:                 # Opening brackets
        stack.append(add_text)
        full_text.append(' ' + add_text)
    elif add_text in closing_chars:                 # Closing brackets
        stack.pop()
        full_text.append(add_text)
    elif prev_text in quote_chars:              # Tokens after quotation-like characters
        if prev_text in stack:      # following opening quote
            full_text.append(add_text)
        else:                       # following closing quote
            full_text.append(' ' + add_text)
    elif prev_text in opening_chars:            # Tokens after opening brackets
        full_text.append(add_text)
    elif prev_text in closing_chars:            # Tokens after closing brackets
        full_text.append(' ' + add_text)
    elif add_text.find('\'') != -1:                 # Contractions
        full_text.append(add_text)
    else:                                       # Everything else
        full_text.append(' ' + add_text)


def reconstruct(new, original):
    """Reconstructs the paragraph structure of the original text by reinserting line breaks lost to GCP NLP. Writes the
    new text to a GenderSwap.txt.

    :param new: New text
    :param original: Original text
    :return: None
    """
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

# Read text to process
# TODO add support for other file types: .doc, .docx, .pdf, and .odt
f1 = open('Test.txt', 'r')
text = f1.read()
f1.close()

# Detects the syntax of the text
tokens = analyze_syntax(text)
swapped = f2m(tokens)
reconstruct(swapped, text)

print('Done')
