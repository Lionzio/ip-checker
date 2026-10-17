# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L4-Q1, sem nenhum código de aluno. Revise antes do merge.
def calcular_requisitos(nome, intensidade):
    if nome == "LUA":
        return intensidade, 1, 0, 10 * intensidade
    elif nome == "SOMBRAS":
        return 0, intensidade, 2, 12 * intensidade
    elif nome == "FAMILIAR":
        return 1, 1, intensidade, 15 * intensidade
    return 0, 0, 0, 0


def possui_ingredientes(moli, lotus, cinzas, custo_moli, custo_lotus, custo_cinzas):
    return moli >= custo_moli and lotus >= custo_lotus and cinzas >= custo_cinzas


def conjurar_feitico(moli, lotus, cinzas, custo_moli, custo_lotus, custo_cinzas, poder_base, nome, feitico_anterior):
    moli -= custo_moli
    lotus -= custo_lotus
    cinzas -= custo_cinzas

    bonus = 0
    if feitico_anterior is not None and feitico_anterior != nome:
        bonus = 5

    poder_obtido = poder_base + bonus
    return moli, lotus, cinzas, poder_obtido, bonus


def main():
    meta = int(input())
    moli = int(input())
    lotus = int(input())
    cinzas = int(input())
    qtd_tentativas = int(input())

    poder_total = 0
    feitico_anterior = None
    primeiro_sucesso = True

    for _ in range(qtd_tentativas):
        linha = input().split()
        nome = linha[0]
        intensidade = int(linha[1])

        c_moli, c_lotus, c_cinzas, poder_base = calcular_requisitos(nome, intensidade)

        if possui_ingredientes(moli, lotus, cinzas, c_moli, c_lotus, c_cinzas):
            moli, lotus, cinzas, poder_obtido, bonus = conjurar_feitico(
                moli, lotus, cinzas, c_moli, c_lotus, c_cinzas, poder_base, nome, feitico_anterior
            )
            poder_total += poder_obtido

            print(f"Melinoë conjurou {nome} e obteve {poder_obtido} de poder.")
            if bonus > 0:
                print("Sinergia lunar ativada! Selene concedeu 5 de poder extra.")
                print("Hécate: A luz de Selene responde à sua feitiçaria. Faça-a valer.")
            else:
                if primeiro_sucesso:
                    print("Hécate: Foi para isto que treinamos todas essas noites, Melinoë.")
                    primeiro_sucesso = False
                else:
                    print("Hécate: Disciplina, Melinoë. Uma bruxa vence antes mesmo de deixar a Encruzilhada.")
            print("Que assim seja!")

            feitico_anterior = nome
        else:
            print(f"Ingredientes insuficientes para conjurar {nome}.")
            print("Hécate: Intenção sem preparo não basta. Reúna os ingredientes e tente outra vez.")

    print()
    print(f"Poder acumulado: {poder_total}")
    print(f"Ingredientes restantes: {moli} moli, {lotus} lotus e {cinzas} cinzas.")

    if poder_total >= meta:
        print("Melinoë está pronta para enfrentar Cronos.")
        print("Hécate: Você está pronta para partir. Lembre-se do que aprendeu na Encruzilhada — e retorne para nós.")
    else:
        print("Melinoë precisa se preparar melhor antes de enfrentar Cronos.")
        print("Hécate: Cronos não terá piedade de você. Eu tampouco terei durante seu treinamento.")


if __name__ == "__main__":
    main()
