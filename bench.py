import os
import time

from bsbi import BSBIIndex
from compression import VBEPostings, StandardPostings, BICPostings

if __name__ == '__main__':
  TRIAL = 10
  FILE_INDEX_NAME = "main_index"
  OUTPUT_DIR = "index"
#   POSTINGS = StandardPostings
#   POSTINGS = VBEPostings
  POSTINGS = BICPostings
  # nltk.download('punkt')

  total_time = 0
  max_time = -1
  min_time = -1
  for j in range(TRIAL):

    start = time.time()
    BSBI_instance = BSBIIndex(data_dir='collection',
                              postings_encoding=POSTINGS,
                              output_dir='index')

    BSBI_instance.index()  # memulai indexing!
    end = time.time()
    duration = end - start
    if (max_time == -1):
      max_time = min_time = duration
    total_time += duration
    max_time = max(duration, max_time)
    min_time = min(duration, min_time)
  print(
    f"Average time indexing for {POSTINGS.__name__}: {(total_time / TRIAL):.5f} seconds")
  # print(f"Min time for {POSTINGS.__name__}: {(min_time):.5f} seconds")
  # print(f"Max time for {POSTINGS.__name__}: {(max_time):.5f} seconds")
  dict_file = os.stat(os.path.join(OUTPUT_DIR, f"{FILE_INDEX_NAME}.dict"))
  index_file = os.stat(os.path.join(OUTPUT_DIR, f"{FILE_INDEX_NAME}.index"))
  print(
    f"dict file size: {dict_file.st_size} Bytes = {dict_file.st_size / 1024} KB")
  print(
    f"index file size: {index_file.st_size} Bytes = {index_file.st_size / 1024} KB")

  BSBI_instance = BSBIIndex(data_dir='collection',
                            postings_encoding=POSTINGS,
                            output_dir='index')

  BSBI_instance.index()  # memulai indexing!
  for j in range(TRIAL):
    queries = ["olahraga", "tumor", "hidup sehat", "jantung", "penyakit",
               "kuat", "badan sehat", "olahraga teratur", "tidur cukup"]
    start = time.time()
    for query in queries:
      ans = sorted(BSBI_instance.retrieve(query))
    end = time.time()
    duration = end - start
    total_time += duration

  print(
    f"Average time searching for {POSTINGS.__name__}: {(total_time / TRIAL):.5f} seconds")
