import pickle
import os

from compression import BICPostings


class InvertedIndex:
    """
    Class yang mengimplementasikan bagaimana caranya scan atau membaca secara
    efisien Inverted Index yang disimpan di sebuah file; dan juga menyediakan
    mekanisme untuk menulis Inverted Index ke file (storage) saat melakukan indexing.

    Attributes
    ----------
    postings_dict: Dictionary mapping:

            termID -> (start_position_in_index_file,
                       number_of_postings_in_list,
                       length_in_bytes_of_postings_list)

        postings_dict adalah konsep "Dictionary" yang merupakan bagian dari
        Inverted Index. postings_dict ini diasumsikan dapat dimuat semuanya
        di memori.

        Seperti namanya, "Dictionary" diimplementasikan sebagai python's Dictionary
        yang memetakan term ID (integer) ke 3-tuple:
           1. start_position_in_index_file : (dalam satu bytes) posisi dimana
              postings yang bersesuaian berada di file (storage). Kita bisa
              menggunakan operasi "seek" untuk mencapainya.
           2. number_of_postings_in_list : berapa banyak docID yang ada pada
              postings
           3. length_in_bytes_of_postings_list : panjang postings list dalam
              satuan byte.

    terms: List[int]
        List of terms IDs, untuk mengingat urutan terms yang dimasukan ke
        dalam Inverted Index.

    """

    def __init__(self, index_name, postings_encoding, directory=''):
        """
        Parameters
        ----------
        index_name (str): Nama yang digunakan untuk menyimpan files yang berisi index
        postings_encoding : Lihat di compression.py, kandidatnya adalah StandardPostings,
                        GapBasedPostings, dsb.
        directory (str): directory dimana file index berada
        """

        self.index_file_path = os.path.join(directory, index_name+'.index')
        self.metadata_file_path = os.path.join(directory, index_name+'.dict')

        self.postings_encoding = postings_encoding
        self.directory = directory

        self.postings_dict = {}
        self.terms = []  # Untuk keep track urutan term yang dimasukkan ke index

    def __enter__(self):
        """
        Memuat semua metadata ketika memasuki context.
        Metadata:
            1. Dictionary ---> postings_dict
            2. iterator untuk List yang berisi urutan term yang masuk ke
                index saat konstruksi. ---> term_iter

        Metadata disimpan ke file dengan bantuan library "pickle"

        Perlu memahani juga special method __enter__(..) pada Python dan juga
        konsep Context Manager di Python. Silakan pelajari link berikut:

        https://docs.python.org/3/reference/datamodel.html#object.__enter__
        """
        # Membuka index file
        self.index_file = open(self.index_file_path, 'rb+')

        # Kita muat postings dict dan terms iterator dari file metadata
        with open(self.metadata_file_path, 'rb') as f:
            self.postings_dict, self.terms = pickle.load(f)
            self.term_iter = self.terms.__iter__()

        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Menutup index_file dan menyimpan postings_dict dan terms ketika keluar context"""
        # Menutup index file
        self.index_file.close()

        # Menyimpan metadata (postings dict dan terms) ke file metadata dengan bantuan pickle
        with open(self.metadata_file_path, 'wb') as f:
            pickle.dump([self.postings_dict, self.terms], f)


class InvertedIndexReader(InvertedIndex):
    """
    Class yang mengimplementasikan bagaimana caranya scan atau membaca secara
    efisien Inverted Index yang disimpan di sebuah file.
    """

    def __iter__(self):
        return self

    def reset(self):
        """
        Kembalikan file pointer ke awal, dan kembalikan pointer iterator
        term ke awal
        """
        self.index_file.seek(0)
        self.term_iter = self.terms.__iter__()  # reset term iterator

    def __next__(self):
        """
        Class InvertedIndexReader juga bersifat iterable (mempunyai iterator).
        Silakan pelajari:
        https://stackoverflow.com/questions/19151/how-to-build-a-basic-iterator

        Ketika instance dari kelas InvertedIndexReader ini digunakan
        sebagai iterator pada sebuah loop scheme, special method __next__(...)
        bertugas untuk mengembalikan pasangan (term, postings_list) berikutnya
        pada inverted index.

        PERHATIAN! method ini harus mengembalikan sebagian kecil data dari
        file index yang besar. Mengapa hanya sebagian kecil? karena agar muat
        diproses di memori. JANGAN MEMUAT SEMUA INDEX DI MEMORI!
        """
        term = next(self.term_iter)
        postings_list = self.get_postings_list(term)
        return (term, postings_list)

    def get_postings_list(self, term):
        """
        Kembalikan sebuah postings list (list of docIDs) untuk sebuah term.

        PERHATIAN! method tidak tidak boleh iterasi di keseluruhan index
        dari awal hingga akhir. Method ini harus langsung loncat ke posisi
        byte tertentu pada file (index file) dimana postings list dari
        term disimpan.
        """
        term_posting_dict = self.postings_dict[term]
        self.index_file.seek(term_posting_dict[0])
        if self.postings_encoding == BICPostings:
            postings_list = self.postings_encoding.decode(
            self.index_file.read(term_posting_dict[2]), n = term_posting_dict[1])
        else:
            postings_list = self.postings_encoding.decode(
                self.index_file.read(term_posting_dict[2]))
        return postings_list


class InvertedIndexWriter(InvertedIndex):
    """
    Class yang mengimplementasikan bagaimana caranya menulis secara
    efisien Inverted Index yang disimpan di sebuah file.
    """

    def __enter__(self):
        self.index_file = open(self.index_file_path, 'wb+')
        return self

    def append(self, term, postings_list):
        """
        Menambahkan (append) sebuah term dan juga postings_list yang terasosiasi
        ke posisi akhir index file.

        Method ini melakukan 3 hal:
        1. Encode postings_list menggunakan self.postings_encoding,
        2. Menyimpan metadata dalam bentuk self.terms dan self.postings_dict.
           Ingat kembali bahwa self.postings_dict memetakan sebuah termID ke
           sebuah 3-tuple: - start_position_in_index_file
                           - number_of_postings_in_list
                           - length_in_bytes_of_postings_list
        3. Menambahkan (append) bystream dari postings_list yang sudah di-encode
           ke posisi akhir index file di harddisk.

        SEARCH ON YOUR FAVORITE SEARCH ENGINE:
        - Anda mungkin mau membaca tentang Python I/O
          https://docs.python.org/3/tutorial/inputoutput.html
          Di link ini juga bisa kita pelajari bagaimana menambahkan informasi
          ke bagian akhir file.
        - Beberapa method dari object file yang mungkin berguna seperti seek(...)
          dan tell()

        Parameters
        ----------
        term:
            term atau termID yang merupakan unique identifier dari sebuah term
        postings_list: List[Int]
            List of docIDs dimana term muncul
        """
        encoded_postings_list = self.postings_encoding.encode(postings_list)
        self.terms.append(term)

        self.postings_dict[term] = (self.index_file.tell(),
                                    len(postings_list),
                                    len(encoded_postings_list))

        self.index_file.write(encoded_postings_list)


if __name__ == "__main__":

    from compression import StandardPostings, VBEPostings

    with InvertedIndexWriter('test', postings_encoding=StandardPostings, directory='./tmp/') as index:
        index.append(1, [2, 3, 4, 8, 10])
        index.append(2, [3, 4, 5])
        index.index_file.seek(0)
        assert index.terms == [1, 2], "terms salah"
        assert index.postings_dict == {1: (0, 5, len(StandardPostings.encode([2, 3, 4, 8, 10]))),
                                       2: (len(StandardPostings.encode([2, 3, 4, 8, 10])), 3,
                                           len(StandardPostings.encode([3, 4, 5])))}, "postings dictionary salah"
        assert StandardPostings.decode(index.index_file.read()) == [
            2, 3, 4, 8, 10, 3, 4, 5], "penyimpanan postings pada harddisk salah"

        index.index_file.seek(index.postings_dict[2][0])
        assert StandardPostings.decode(index.index_file.read(
            len(StandardPostings.encode([3, 4, 5])))) == [3, 4, 5], "posisi postings salah"

        index.index_file.seek(0)
        assert StandardPostings.decode(index.index_file.read(index.postings_dict[1][2])) == [
            2, 3, 4, 8, 10], "posisi postings salah"
        assert StandardPostings.decode(index.index_file.read(
            index.postings_dict[2][2])) == [3, 4, 5], "posisi postings salah"

    with InvertedIndexWriter('test', postings_encoding=VBEPostings, directory='./tmp/') as index:
        index.append(1, [2, 3, 4, 8, 10])
        index.append(2, [3, 4, 5])
        index.index_file.seek(0)
        assert index.terms == [1, 2], "terms salah"
        assert index.postings_dict == {1: (0, 5, len(VBEPostings.encode([2, 3, 4, 8, 10]))),
                                       2: (len(VBEPostings.encode([2, 3, 4, 8, 10])), 3,
                                           len(VBEPostings.encode([3, 4, 5])))}, "postings dictionary salah"
        assert VBEPostings.decode(index.index_file.read()) == [
            2, 3, 4, 8, 10, 13, 14, 15], "penyimpanan postings pada harddisk salah"

        index.index_file.seek(index.postings_dict[2][0])
        assert VBEPostings.decode(index.index_file.read(
            len(VBEPostings.encode([3, 4, 5])))) == [3, 4, 5], "terdapat kesalahan"

        index.index_file.seek(0)
        assert VBEPostings.decode(index.index_file.read(index.postings_dict[1][2])) == [
            2, 3, 4, 8, 10], "terdapat kesalahan"
        assert VBEPostings.decode(index.index_file.read(index.postings_dict[2][2])) == [
            3, 4, 5], "terdapat kesalahan"
