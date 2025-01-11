import base64
from solders.transaction import Transaction

tx_string = "AdK9X3Ry8rn4hn+sCfQqWkHSWTPKvv70EEkBaKqK4i7BzrqTYo0HEqpIfX4y7/MKVjeG3EX1w4kXcuTdNMzyQwkBAAIEG4bfFKeMUx/1Ixu1steja9p/MbVVKPCJu9PKHEHDPakT1XF7FmyR/auZ64M/M+d6wKitxlHAojC95G+Ztxnf8QAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAwZGb+UhFzL/7K26csOb57yM5bvF9xJrLEObOkAAAACQb5T2ezOTfTfMJpRzyVnzLzs2p0iPM6iSpwRP8tL/UAMDAAkDAC0xAQAAAAADAAUC9AEAAAICAAEMAgAAAMDGLQAAAAAA"
decoded_bytes = base64.b64decode(tx_string)

print(Transaction.from_bytes(decoded_bytes))