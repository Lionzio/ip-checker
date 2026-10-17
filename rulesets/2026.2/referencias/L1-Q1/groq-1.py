# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-120b, 17/10/2026.
# Só a partir do enunciado da L1-Q1, sem nenhum código de aluno. Revise antes do merge.
def main():
    try:
        G = int(input().strip())
    except:
        G = 0

    print("Nossa, que lindo cavalo! Mas deixe-me verificar apenas uma coisa...")
    if G == 0:
        print("ENTRADA LIBERADA")
    else:
        print("ARMADILHA")
        duplas = G // 2
        if G % 2 == 0:
            print(f"OS GUERREIROS FORMARAM {duplas} DUPLAS")
        else:
            print(f"OS GUERREIROS FORMARAM {duplas} DUPLAS E UM GUERREIRO FICOU SOZINHO")

if __name__ == "__main__":
    main()
