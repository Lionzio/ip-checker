# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L4-Q5, sem nenhum código de aluno. Revise antes do merge.
def bubble_sort(lista):
    n = len(lista)
    for i in range(n):
        for j in range(0, n - i - 1):
            if lista[j] > lista[j + 1]:
                lista[j], lista[j + 1] = lista[j + 1], lista[j]
    return lista


def tartaro():
    entrada = input().strip()
    nomes = [n.strip() for n in entrada.split(",")]
    bubble_sort(nomes)
    print(f"Zagreu: Aqui está sua papelada: {', '.join(nomes)}")
    print()


def loop_bencaos(bencaos_obtidas):
    deuses_validos = {
        "AFRODITE",
        "ARES",
        "ARTEMIS",
        "ATENA",
        "DEMETER",
        "DIONISIO",
        "HERMES",
        "POSEIDON",
        "ZEUS",
    }
    total_novas = 0
    while True:
        linha = input().strip()
        if linha == "PARAR":
            print()
            break
        elif linha in deuses_validos:
            print(f"Zagreu obteve uma Bênção de {linha}.")
            bencaos_obtidas.add(linha)
            total_novas += 1
        elif linha == "COMBINADA":
            c1 = input().strip()
            c2 = input().strip()

            inv1 = c1 not in deuses_validos
            inv2 = c2 not in deuses_validos
            nao_obtida1 = c1 not in bencaos_obtidas
            nao_obtida2 = c2 not in bencaos_obtidas
            iguais = c1 == c2
            tem_hermes = c1 == "HERMES" or c2 == "HERMES"

            if inv1 or inv2:
                print(
                    "Zagreu: Uma Bênção Combinada assim? Acho que você está brincando comigo."
                )
            elif nao_obtida1 or nao_obtida2:
                print(
                    "Zagreu: Eu ainda não tenho nenhuma Bênção desse(a) Deus(a), não posso combiná-la"
                )
            elif iguais:
                print(
                    "Zagreu: Os dois Deuses precisam diferentes para realizar uma Bênção Combinada..."
                )
            elif tem_hermes:
                print(
                    "Zagreu: Uma Bênção Combinada com Hermes? Acho que ele é competitivo demais pra cooperar com os outros."
                )
            else:
                print(
                    f"Zagreu foi abençoado por uma Bênção Combinada de {c1} e {c2}."
                )
                bencaos_obtidas.add(c1)
                total_novas += 1
        else:
            print(
                f"Zagreu: Ah, claro. A Bênção de {linha}. Como pude esquecer? Tenho certeza de que meu pai também deve ter esquecido de mencioná-lo(a)... Você está brincando comigo não é?."
            )
    return total_novas


def asfodelo():
    m1 = []
    for _ in range(3):
        m1.append([int(x) for x in input().strip().split()])
    m2 = []
    for _ in range(3):
        m2.append([int(x) for x in input().strip().split()])

    res = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    for i in range(3):
        for j in range(3):
            for k in range(3):
                res[i][j] += m1[i][k] * m2[k][j]

    maior = res[0][0]
    l_maior, c_maior = 0, 0
    for i in range(3):
        for j in range(3):
            if res[i][j] > maior:
                maior = res[i][j]
                l_maior, c_maior = i, j

    print(
        f"Zagreu: devo lançar minha vara de pesca nesse ponto: ({l_maior}, {c_maior})"
    )
    print()


def elisio():
    legado_total = 0.0
    while legado_total < 200:
        texto = input().strip()
        partes = texto.split(" O ")
        nome = partes[0]
        titulo = partes[1] if len(partes) > 1 else ""

        if nome == "Hércules":
            base = 50.0
        elif nome == "Aquiles":
            base = 40.0
        elif nome == "Odisseu":
            base = 35.0
        else:
            base = 20.0

        if titulo == "Imortal":
            legado_obtido = base * 1.5
        elif titulo == "Forte":
            legado_obtido = base * 1.2
        elif titulo == "Grande":
            legado_obtido = base + 15
        else:
            legado_obtido = base + 10

        legado_total += legado_obtido

        if legado_obtido.is_integer():
            legado_str = str(int(legado_obtido))
        else:
            legado_str = str(legado_obtido)

        print(
            f"O Herói: {nome} O {titulo} adicionou {legado_str} pontos de Legado."
        )

    print("Zagreu: Acho que já fizemos história o suficiente por hoje.")
    print()


def estige(bencaos_totais):
    print("O Templo de Estige... o último obstáculo entre você e a superfície.")
    print()

    vida_zagreu = 100
    vida_hades = 200
    hades_ataques_count = 0
    hades_segunda_fase = False

    while vida_zagreu > 0 and vida_hades > 0:
        if (hades_ataques_count % 3) == 2:
            print(
                "Zagreu: Meu pai parece estar carregando um forte ataque, é melhor desviar!"
            )

        acao = input().strip()

        if acao == "ATACAR":
            dano = 20
            vida_hades -= dano
            print(f"Zagreu golpeia Hades, causando {dano} de dano.")
        elif acao == "ATAQUE ESPECIAL":
            dano = 40
            vida_hades -= dano
            print(
                f"Zagreu golpeia Hades com um ataque especial, causando {dano} de dano."
            )
        elif acao == "ESQUIVA":
            print(f"Zagreu esquiva do ataque de Hades, evitando o dano.")

        if vida_hades <= 100 and not hades_segunda_fase:
            hades_segunda_fase = True
            print()
            print("Hades: Chega! Isso acaba agora!")
            print()

        if vida_hades <= 0:
            print()
            print(
                "O senhor do Submundo cai diante de Zagreu. Pela primeira vez, não há nada entre ele e a superfície."
            )
            print("O portão se abre diante de você.")
            print(
                "Zagreu finalmente deixa o Submundo para trás e sente o calor do sol tocar seu rosto. Pela primeira vez, a superfície está diante de seus olhos."
            )
            print("Você conseguiu escapar. A tentativa foi concluída.")
            return

        hades_ataques_count += 1
        forte = (hades_ataques_count % 3) == 0

        if hades_segunda_fase:
            dano_hades = 100 if forte else 25
        else:
            dano_hades = 50 if forte else 15

        if acao == "ESQUIVA":
            pass
        else:
            vida_zagreu -= dano_hades
            if forte:
                print("Hades: Desapareça!")
            print(f"Hades causou {dano_hades} de dano em Zagreu.")

        if vida_zagreu <= 0:
            print()
            print("Zagreu: Me desculpe, mãe. Foi tão perto...")
            return


def main():
    print(
        "O portão se abre diante de você, revelando o caminho para o Submundo. Uma nova tentativa começa agora."
    )
    print()

    bencaos_obtidas = set()
    bencaos_totais = 0

    # Tártaro
    tartaro()
    bencaos_totais += loop_bencaos(bencaos_obtidas)
    if bencaos_totais < 3:
        print(
            "Zagreu cai, derrotado mais uma vez. Seu corpo se desfaz, retornando ao lugar que conhece tão bem."
        )
        return

    # Asfódelo
    asfodelo()
    bencaos_totais += loop_bencaos(bencaos_obtidas)
    if bencaos_totais < 6:
        print(
            "Zagreu cai, derrotado mais uma vez. Seu corpo se desfaz, retornando ao lugar que conhece tão bem."
        )
        return

    # Elísio
    elisio()
    bencaos_totais += loop_bencaos(bencaos_obtidas)
    if bencaos_totais < 9:
        print(
            "Zagreu cai, derrotado mais uma vez. Seu corpo se desfaz, retornando ao lugar que conhece tão bem."
        )
        return

    # Templo de Estige
    estige(bencaos_totais)


if __name__ == "__main__":
    main()
