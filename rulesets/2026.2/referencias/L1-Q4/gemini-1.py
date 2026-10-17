# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L1-Q4, sem nenhum código de aluno. Revise antes do merge.
def main():
    chovendo = input().strip()
    temperatura = int(input())
    energia = int(input())

    if chovendo == "S":
        if energia > 3:
            print("Brincar de bolinha no laboratório")
        else:
            print("Soneca na caminha do CIn")
    else:
        if temperatura > 30:
            if energia >= 4:
                print("Nadar no lago da UFPE")
            else:
                print("Descansar na sombra da árvore")
        elif temperatura < 15:
            print("Passeio com roupinha de frio")
        else:
            if energia > 2:
                print("Longo passeio no parque")
            else:
                print("Passeio curto no quarteirão")

if __name__ == "__main__":
    main()
