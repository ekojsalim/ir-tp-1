import array
import math
from bitstring import BitStream, BitString, pack
from bitarray import bitarray
from bitarray.util import int2ba, ba2int


class StandardPostings:
    """ 
    Class dengan static methods, untuk mengubah representasi postings list
    yang awalnya adalah List of integer, berubah menjadi sequence of bytes.
    Kita menggunakan Library array di Python.

    ASUMSI: postings_list untuk sebuah term MUAT di memori!

    Silakan pelajari:
        https://docs.python.org/3/library/array.html
    """

    @staticmethod
    def encode(postings_list):
        """
        Encode postings_list menjadi stream of bytes

        Parameters
        ----------
        postings_list: List[int]
            List of docIDs (postings)

        Returns
        -------
        bytes
            bytearray yang merepresentasikan urutan integer di postings_list
        """
        # Untuk yang standard, gunakan L untuk unsigned long, karena docID
        # tidak akan negatif. Dan kita asumsikan docID yang paling besar
        # cukup ditampung di representasi 4 byte unsigned.
        return array.array('L', postings_list).tobytes()

    @staticmethod
    def decode(encoded_postings_list):
        """
        Decodes postings_list dari sebuah stream of bytes

        Parameters
        ----------
        encoded_postings_list: bytes
            bytearray merepresentasikan encoded postings list sebagai keluaran
            dari static method encode di atas.

        Returns
        -------
        List[int]
            list of docIDs yang merupakan hasil decoding dari encoded_postings_list
        """
        decoded_postings_list = array.array('L')
        decoded_postings_list.frombytes(encoded_postings_list)
        return decoded_postings_list.tolist()


class BICPostings:
    @staticmethod
    def bit_representation(x, r):
        """
        Get bit representation of x using ceil(log2(r + 1)) bits
        """
        b = len(int2ba(r))
        return int2ba(x, b)

    @staticmethod
    def bic_encode(s, n, lo, hi):
        out = bitarray()
        stack = []

        # offset, n, low, high
        stack.append((0, n, lo, hi))

        while len(stack) > 0:
            o, n, lo, hi = stack.pop()

            m = n // 2
            x = s[m + o]
            out.extend(BICPostings.bit_representation(x - lo - m, hi - lo - n + 1))

            # right side
            if (n2 := n - m - 1) > 0:
                stack.append((o + m + 1, n2, x + 1, hi))
            
            # left side
            if (n1 := m) > 0:
                stack.append((o, n1, lo, x - 1))

        return out

    @staticmethod
    def encode(postings_list, write_n=False):
        if len(postings_list) == 0:
            return bitarray().tobytes()

        out = bitarray()

        # write hi
        hi = postings_list[-1]
        hi_bit_length = max(hi.bit_length(), 1) # sometimes we get 0, default to 1
        out.extend(int2ba(hi_bit_length, 5))
        out.extend(int2ba(hi, hi_bit_length))

        n = len(postings_list)

        # write BIC encoding
        if n > 1:
            encoded = BICPostings.bic_encode(postings_list[:-1], n - 1, 0, hi)
            out.extend(encoded)
        return out.tobytes()

    @staticmethod
    def bic_decode(a, n, lo, hi):
        out = [0] * n

        stack = []
        
        stack.append((0, n, lo, hi))

        pos = 0
        while len(stack) > 0:
            o, n, lo, hi = stack.pop()

            m = n // 2
            r = hi - lo - n + 1
            l = len(int2ba(r))
            x = ba2int(a[pos: pos + l]) + lo + m

            out[m + o] = x
            pos += l

            if (n2 := n - m - 1) > 0:
                stack.append((o + m + 1, n2, x + 1, hi))

            if (n1 := m) > 0:
                stack.append((o, n1, lo, x - 1))

        return out

    @staticmethod
    def decode(encoded_bytestream, n):
        if n == 0:
            return []
        a = bitarray()
        stream = a.frombytes(encoded_bytestream)
        # get hi
        hi_bit_length = ba2int(a[:5])
        hi = ba2int(a[5:5 + hi_bit_length])
        decoded = []
        if n > 1:
            decoded = BICPostings.bic_decode(a[5 + hi_bit_length:], n - 1, 0, hi)
        decoded.append(hi)
        return decoded


class VBEPostings:
    """ 
    Berbeda dengan StandardPostings, dimana untuk suatu postings list,
    yang disimpan di disk adalah sequence of integers asli dari postings
    list tersebut apa adanya.

    Pada VBEPostings, kali ini, yang disimpan adalah gap-nya, kecuali
    posting yang pertama. Barulah setelah itu di-encode dengan Variable-Byte
    Enconding algorithm ke bytestream.

    Contoh:
    postings list [34, 67, 89, 454] akan diubah dulu menjadi gap-based,
    yaitu [34, 33, 22, 365]. Barulah setelah itu di-encode dengan algoritma
    compression Variable-Byte Encoding, dan kemudian diubah ke bytesream.

    ASUMSI: postings_list untuk sebuah term MUAT di memori!

    """

    @staticmethod
    def vb_encode_number(number):
        """
        Encodes a number using Variable-Byte Encoding
        Lihat buku teks kita!
        """
        bytes = []
        while True:
            bytes.insert(0, number % 128)  # prepend ke depan
            if number < 128:
                break
            number = number // 128
        bytes[-1] += 128  # bit awal pada byte terakhir diganti 1
        return array.array('B', bytes).tobytes()

    @staticmethod
    def vb_encode(list_of_numbers):
        """ 
        Melakukan encoding (tentunya dengan compression) terhadap
        list of numbers, dengan Variable-Byte Encoding
        """
        bytes = []
        for number in list_of_numbers:
            bytes.append(VBEPostings.vb_encode_number(number))
        return b"".join(bytes)

    @staticmethod
    def encode(postings_list):
        """
        Encode postings_list menjadi stream of bytes (dengan Variable-Byte
        Encoding). JANGAN LUPA diubah dulu ke gap-based list, sebelum
        di-encode dan diubah ke bytearray.

        Parameters
        ----------
        postings_list: List[int]
            List of docIDs (postings)

        Returns
        -------
        bytes
            bytearray yang merepresentasikan urutan integer di postings_list
        """
        list_of_gaps = [postings_list[0]] + [b - a for a,
                                             b in zip(postings_list, postings_list[1:])]
        return VBEPostings.vb_encode(list_of_gaps)

    @staticmethod
    def vb_decode(encoded_bytestream):
        """
        Decoding sebuah bytestream yang sebelumnya di-encode dengan
        variable-byte encoding.
        """
        decoded_bytestream = array.array("B")
        decoded_bytestream.frombytes(encoded_bytestream)
        numbers = []
        n = 0
        for b in decoded_bytestream:
            if b < 128:
                n = 128 * n + b
            else:
                n = 128 * n + (b - 128)
                numbers.append(n)
                n = 0
        return numbers

    @staticmethod
    def decode(encoded_postings_list):
        """
        Decodes postings_list dari sebuah stream of bytes. JANGAN LUPA
        bytestream yang di-decode dari encoded_postings_list masih berupa
        gap-based list.

        Parameters
        ----------
        encoded_postings_list: bytes
            bytearray merepresentasikan encoded postings list sebagai keluaran
            dari static method encode di atas.

        Returns
        -------
        List[int]
            list of docIDs yang merupakan hasil decoding dari encoded_postings_list
        """
        decoded_list_of_gaps = VBEPostings.vb_decode(encoded_postings_list)
        start = 0
        decoded_postings_list = [
            start := start + a for a in decoded_list_of_gaps]
        return decoded_postings_list


if __name__ == '__main__':
    postings_list = [34, 67, 89, 454, 2345738]
    # import random
    # for i in range (100*500):
    # postings_list.append(postings_list[-1] + random.randint(1, 1000))
    for Postings in [StandardPostings, VBEPostings, BICPostings]:
        print(Postings.__name__)
        encoded_postings_list = Postings.encode(postings_list)
        print("byte hasil encode: ", encoded_postings_list)
        print("ukuran encoded postings: ", len(encoded_postings_list), "bytes")
        decoded_posting_list = Postings.decode(encoded_postings_list) if Postings != BICPostings else Postings.decode(
            encoded_postings_list, n=len(postings_list))
        print("hasil decoding: ", decoded_posting_list)
        assert decoded_posting_list == postings_list, "hasil decoding tidak sama dengan postings original"
        print()
