# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-20b, 17/10/2026.
# Só a partir do enunciado da L5-Q1, sem nenhum código de aluno. Revise antes do merge.
def main():
    inventory = {}
    while True:
        try:
            action = input().strip()
        except EOFError:
            break
        if action == "FIM":
            break
        name = input().strip()
        quantity = int(input().strip())
        if action == "ADICIONAR":
            inventory[name] = inventory.get(name, 0) + quantity
        elif action == "REMOVER":
            if name not in inventory:
                print("ERRO! Item não está no Inventário!")
            elif inventory[name] < quantity:
                print("ERRO! Quantidade insuficiente no Inventário!")
            else:
                inventory[name] -= quantity
                if inventory[name] == 0:
                    del inventory[name]
    if not inventory:
        print("Inventário Vazio!")
    else:
        for name, qty in inventory.items():
            print(f"{name} - {qty}")

if __name__ == "__main__":
    main()
