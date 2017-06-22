#!usr/bin/env python
# -*-coding:utf-8-*-
import jieba
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
from pdfminer.layout import *
from pdfminer.converter import PDFPageAggregator
import ConfigParser
import os
import sys, getopt
import re

suffix_num_puctuation = [',', '.', '%']
perfix_num_puctuation = ['+', '-']
num_chars = [u"一", u"二", u"三", u"四", u"五", u"六", u"七", u"八", u"九", u"十", u"壹", u"贰", u"叁", u"肆", u"伍", u"陆", u"柒", u"捌",
             u"玖", u"拾", u"万", u"元", u"亿"]

# 用于存储最终结果
result = {}
# 用于存储分词结果的数组
text_words = []

# 索引，记录所有的keywords, 及其对应的ori keywords
keyword_index = {}
# 记录所有的keywords，用于匹配
keywords_all = {}
# 记录所有word_keyword的对应的candidates
word_candidates = {}

def is_num(text):
  if text.isdigit():
    return True
  pattern = re.compile(r'^[+-]*[0-9]+\.[0-9]+$')
  if pattern.match(text):
    return True
  for t in unicode(text, "utf-8"):
    if t not in num_chars:
      return False
  return True

def is_perfix_num_punctuation(text):
  if len(text) == 1 and (text in perfix_num_puctuation):
    return True
  return False

def is_suffix_num_punctuation(text):
  if len(text) == 1 and (text in suffix_num_puctuation):
    return True
  return False

# type 0: num_keyword, type 1: word_keyword, type 2: sentence_keyword
def load_keywords(confFile):
  cf = ConfigParser.ConfigParser()
  cf.readfp(open(confFile))
  # get all key-value pairs in section 'keyword'
  keywords = cf.items("num_keyword")
  for keyword in keywords:
    tokens = keyword[1].split("|")
    for token in tokens:
      if token not in keyword_index:
        keyword_index[token] = keyword[0]
      if token not in keywords_all:
        keywords_all[token] = 0
  keywords = cf.items("word_keyword")
  for keyword in keywords:
    if keyword[0] not in keywords_all:
      keywords_all[keyword[0]] = 1
    if keyword[0] not in keyword_index:
      keyword_index[keyword[0]] = keyword[0]
    if keyword[0] not in word_candidates:
      word_candidates[keyword[0]] = []
    tokens = keyword[1].split("|")
    for token in tokens:
      word_candidates[keyword[0]].append(token)
  keywords = cf.items("sentence_keyword")
  for keyword in keywords:
    tokens = keyword[1].split("|")
    for token in tokens:
      if token not in keyword_index:
        keyword_index[token] = keyword[0]
      if token not in keywords_all:
        keywords_all[token] = 2

def word_cut(inputFile):
  fp = open(inputfile)
  # 来创建一个pdf文档分析器
  parser = PDFParser(fp)
  # 创建一个PDF文档对象存储文档结构
  document = PDFDocument(parser)

  # 检查文件是否允许文本提取
  if not document.is_extractable:
      raise PDFTextExtractionNotAllowed
  else:
    # 创建一个PDF资源管理器对象来存储共赏资源
    rsrcmgr = PDFResourceManager()
    # 设定参数进行分析
    laparams = LAParams()
    # 创建一个PDF设备对象
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    # 创建一个PDF解释器对象
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    # 处理每一页
    # NOTE(lijiangdong): page num 好像没啥用，而且按照页数且分会丢信息
    for page in PDFPage.create_pages(document):
      interpreter.process_page(page)
      # 接受该页面的LTPage对象
      layout = device.get_result()
      for x in layout:
        if (isinstance(x, LTTextBoxHorizontal)):
          line = x.get_text().encode('utf-8')
          seg_list = jieba.cut(line, cut_all=False)
          for a in seg_list:
            b = a.strip()
            if len(b) == 0:
              continue
            text_words.append(b.encode('utf-8'));
    #f1.write('|'.join(text_words))
    #f1.write("\n")
    #f1.close()
    extract()


def extract():
  for a in range(0, len(text_words)):
    if text_words[a] not in keywords_all:
      continue
    r = ""
    if keywords_all[text_words[a]] == 0:
      end = a + 10
      if end > len(text_words):
        end = len(text_words)
      for b in range(a + 1, end):
        if len(r) == 0 and (text_words[b] == ':' or is_suffix_num_punctuation(text_words[b])):
          continue
        if len(r) == 0:
          if is_perfix_num_punctuation(text_words[b]):
            r = r + text_words[b]
            continue
          if is_suffix_num_punctuation(text_words[b]) == False and is_num(text_words[b]) == False:
            continue
        if len(r) != 0 and (text_words[b] == ':' or (is_num(text_words[b]) == False and is_suffix_num_punctuation(text_words[b]) == False)):
          break
        r = r + text_words[b]
      if len(r) == 0:
        continue
      index = keyword_index[text_words[a]]
      if index not in result:
        result[index] = r
      else:
        result[index] = result[index] + "^" + r
      a = end 
    elif keywords_all[text_words[a]] == 1:
      if text_words[a] not in word_candidates:
        continue
      candidates = word_candidates[text_words[a]]
      end = a + 10
      if end > len(text_words):
        end = len(text_words)
      for b in range(a + 1, end):
        if text_words[b] not in candidates:
          continue
        index = keyword_index[text_words[a]]
        if index not in result:
          result[index] = text_words[b]
        else:
          result[index] = result[index] + "^" + text_words[b]
      a = end
    elif keywords_all[text_words[a]] == 2:
      b = a + 1
      end = a + 300
      if end > len(text_words):
        end = len(text_words)
      while b < end and not text_words[b] == "。":
        r = r + text_words[b]
        b = b + 1
      index = keyword_index[text_words[a]]
      if r.find("...") == -1:
        if index not in result:
          result[index] = r
        else:
          result[index] = result[index] + "^" + r
      a = b
    else:
      print "error type of keyword" + text_words[a]+ "\t" + keywords_all[text_words[a]]

def output(outFile):
  fout = open(outFile, 'w')
  for r in result:
    fout.write('%s:\t%s\n' % (r, result[r]))
  fout.close()

if __name__ == "__main__":
  inputfile = ''
  outputfile = ''
  try:
    opts, args = getopt.getopt(sys.argv[1:], "hd:k:i:o:", ["dfile=", "kfile=", "ifile=", "ofile="])
  except getopt.GetoptError as err:
    print str(err)
    print 'info-extractor.py -d <user-defined dictionary> -k <keywords file> -i <input file> -o <output file>'
    sys.exit(2)
  for opt, arg in opts:
    if opt == '-h':
      print 'info-extractor.py -d <user-defined dictionary> -k <keywords file> -i <input file> -o <output file>'
      sys.exit()
    elif opt in ("-d", "--dfile"):
      # load user-defined dictionary
      jieba.load_userdict(arg)
    elif opt in ("-k", "--kfile"):
      # load keywords
      load_keywords(arg)
    elif opt in ("-i", "--ifile"):
      inputfile = arg
    elif opt in ("-o", "--ofile"):
      outputfile = arg
  word_cut(inputfile)
  output(outputfile)
