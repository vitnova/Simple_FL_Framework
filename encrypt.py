from Crypto import Random
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_pkcs1_v1_5
from Crypto.Signature import PKCS1_v1_5 as Signature_pkcs1_v1_5
from Crypto.Hash import SHA
import base64

def key_gen(path):
	random_generator = Random.new().read
	rsa = RSA.generate(1024, random_generator)
	private_pem = rsa.exportKey()
	with open(path + "/private.pem", "wb") as f:
		f.write(private_pem)
	public_pem = rsa.publickey().exportKey()
	with open(path + "/public.pem", "wb") as f:
		f.write(public_pem)

	return (bytes.decode(public_pem), bytes.decode(private_pem))

def _encrypt(msg, path, key_name, length = 100):
	pubobj = RSA.importKey(open(path + "/" + key_name + ".pem").read())
	pubobj = Cipher_pkcs1_v1_5.new(pubobj)
	res = []
	for i in range(0, len(msg), length):
		res.append(
			str(
				base64.b64encode(pubobj.encrypt(
				msg[i:i + length].encode(encoding="utf-8"))), 'utf-8'
			)
		)

	return "".join(res)

def encrypt_with_public_key(msg, path):
	return _encrypt(msg, path, "public")

def encrypt_with_private_key(msg, path):
	return _encrypt(msg, path, "private")

def _decrypt(cipher_text, path, key_name, length = 172):
	privobj = RSA.importKey(open(path + "/" + key_name + ".pem").read())
	privobj = Cipher_pkcs1_v1_5.new(privobj)
	res = []
	for i in range(0, len(cipher_text), length):
		res.append(
			str(
				privobj.decrypt(
				base64.b64decode(cipher_text[i:i + length])
				, 'xyz'), 'utf-8'
			)
		)
	return "".join(res)

def decrypt_with_public_key(msg, path):
	return _decrypt(msg, path, "public")

def decrypt_with_private_key(msg, path):
	return _decrypt(msg, path, "private")