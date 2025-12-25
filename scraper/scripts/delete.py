import os
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index_name = os.getenv("PINECONE_INDEX")

# Safety confirmation
confirm = input(f"⚠️  Are you sure you want to delete ALL vectors from index '{index_name}'? (yes/no): ")
if confirm.lower() != "yes":
    print("❌ Deletion cancelled")
    exit()

index = pc.Index(index_name)
index.delete(delete_all=True)
print(f"✅ All vectors deleted from index '{index_name}'")