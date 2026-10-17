# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L5-Q1, sem nenhum código de aluno. Revise antes do merge.
def main():
    inventario = {}

    while True:
        acao = input()
        if acao == "FIM":
            break
        
        item = input()
        qtd = int(input())

        if acao == "ADICIONAR":
            if item in inventario:
                inventario[item] += qtd
            else:
                inventario[item] = qtd
        elif acao == "REMOVER":
            if item not in inventario:
                print("ERRO! Item não está no Inventário!")
            elif qtd > inventario[item]:
                print("ERRO! Quantidade insuficiente no Inventário!")
            else:
                inventario[item] -= qtd
                if inventario[item] == 0:
                    del inventario[item]

    if not inventario:
        print("Inventário Vazio!")
    else:
        for item, qtd in inventario.items():
            print(f"{item} - {qtd}")

if __name__ == "__main__":
    main()
