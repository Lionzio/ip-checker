# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L5-Q1, sem nenhum código de aluno. Revise antes do merge.
def main():
    inventario = {}

    while True:
        acao = input().strip()
        if acao == "FIM":
            break
        
        nome_item = input().strip()
        quantidade_item = int(input().strip())

        if acao == "ADICIONAR":
            if nome_item in inventario:
                inventario[nome_item] += quantidade_item
            else:
                inventario[nome_item] = quantidade_item
        elif acao == "REMOVER":
            if nome_item not in inventario:
                print("ERRO! Item não está no Inventário!")
            elif inventario[nome_item] < quantidade_item:
                print("ERRO! Quantidade insuficiente no Inventário!")
            else:
                inventario[nome_item] -= quantidade_item
                if inventario[nome_item] == 0:
                    del inventario[nome_item]

    if not inventario:
        print("Inventário Vazio!")
    else:
        for item, qtd in inventario.items():
            print(f"{item} - {qtd}")

if __name__ == "__main__":
    main()
