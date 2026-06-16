from ai_agent import assess_initiative
from utils import print_assessment


def main():
    print("Agente avaliador de iniciativas de IA")
    print("Digite a descrição da iniciativa e pressione ENTER.")
    print("Para encerrar, deixe vazio e pressione ENTER.\n")

    while True:
        user_input = input("Iniciativa: ").strip()

        if not user_input:
            print("Encerrando.")
            break

        try:
            result = assess_initiative(user_input)
            print_assessment(result)
        except Exception as e:
            print(f"\nErro ao avaliar iniciativa: {e}\n")


if __name__ == "__main__":
    main()
