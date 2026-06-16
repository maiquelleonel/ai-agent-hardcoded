from pathlib import Path

# Diretórios
EMBEDDINGS_DIR = Path("data/embeddings")
DATA_DIR = Path("data/assessments")
REVIEW_DIR = Path("data/reviews")

# Arquivos
DB_FILE = Path("assessments.json")

# Configurações de Sessão
SESSION_MEMORY = []
MAX_SESSION_ITEMS = 5


# Função para garantir que os diretórios existam
def ensure_directories():
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
