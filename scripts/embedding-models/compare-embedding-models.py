from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

sentences = [
    "Привет, как поживаешь?", 
    "Привет, как ты?",         
    "Сегодня утром он поехал на работу" 
]

print("Starting script\n")

miniLM_L6 = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
embeddings_L6 = miniLM_L6.encode(sentences)

miniLM_L12 = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
embeddings_L12 = miniLM_L12.encode(sentences)

rupert_turbo = SentenceTransformer('sergeyzh/rubert-tiny-turbo')
embeddings_rupert = rupert_turbo.encode(sentences)

def print_similarity(embeddings, model_name):    
    print(f"\n{'='*50}")
    print(f"Модель: {model_name}")
    print('='*50)

    sim_matrix = cosine_similarity(embeddings)
    
    sim_1_2 = sim_matrix[0][1]
    print(f"1) Сходство между (1) и (2) [близкие]: {sim_1_2:.4f}")
    
    sim_1_3 = sim_matrix[0][2]
    print(f"2) Сходство между (1) и (3) [далекие]: {sim_1_3:.4f}")
    
    print(f"3) Разница (близкие - далекие): {sim_1_2 - sim_1_3:.4f}")

print_similarity(embeddings_L6, "all-MiniLM-L6-v2")
print_similarity(embeddings_L12, "paraphrase-multilingual-MiniLM-L12-v2")
print_similarity(embeddings_rupert, "sergeyzh/rubert-tiny-turbo")
    