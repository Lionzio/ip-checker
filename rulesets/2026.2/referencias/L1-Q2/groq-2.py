# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-120b, 17/10/2026.
# Só a partir do enunciado da L1-Q2, sem nenhum código de aluno. Revise antes do merge.
def main():
    energia = int(input().strip())
    petiscos = int(input().strip())
    agua = int(input().strip())
    bateria = int(input().strip())
    gps = input().strip().lower()
    bolinha = input().strip().lower()
    chuva = input().strip().lower()
    temperatura = int(input().strip())
    intensidade = int(input().strip())

    preparo = 0
    print("Byte recebeu um novo chamado! Preparando-se para a aventura...")

    # Energia
    if energia >= 70:
        preparo += 2
        print("Byte está cheio de energia!")
    elif energia < 30:
        preparo -= 2
        print("Byte está muito cansado... A missão ficou mais difícil.")

    # Suprimentos
    if petiscos >= 2 and agua >= 1:
        preparo += 2
        print("Suprimentos preparados!")

    # Coleira tecnológica
    if bateria >= 50 and gps == "sim":
        preparo += 2
        print("Coleira tecnológica preparada!")

    # Bateria crítica
    if bateria <= 20:
        preparo -= 1
        print("A bateria da coleira está crítica! Isso pode atrapalhar a missão.")

    # Motivação especial
    if bolinha == "sim" or petiscos >= 4:
        preparo += 1
        print("Byte está ainda mais animado para a aventura!")

    # Condições adversas
    if chuva == "sim" or temperatura > 32:
        preparo -= 2
        print("O clima não está ajudando... Isso vai dificultar a missão.")

    # Sinal misterioso
    if intensidade >= 70:
        preparo += 1
        print("O sinal está forte! Há algo estranho por perto...")

    print()
    print(f"Nível de preparo: {preparo}")
    if preparo >= 5:
        print("Byte está pronto! A nova aventura começa agora!")
    else:
        print("Byte ainda não está pronto. Melhor se preparar um pouco mais!")


if __name__ == "__main__":
    main()
