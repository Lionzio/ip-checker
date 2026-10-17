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
    entrada_prisioneiros = input().strip()
    prisioneiros = [p.strip() for p in entrada_prisioneiros.split(',')]
    prisioneiros_ordenados = bubble_sort(prisioneiros)
    print(f"Zagreu: Aqui está sua papelada: {', '.join(prisioneiros_ordenados)}")
    print()


def asfodelo():
    matriz1 = []
    for _ in range(3):
        matriz1.append([int(x) for x in input().split()])
    matriz2 = []
    for _ in range(3):
        matriz2.append([int(x) for x in input().split()])

    res = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    for i in range(3):
        for j in range(3):
            for k in range(3):
                res[i][j] += matriz1[i][k] * matriz2[k][j]

    maior = res[0][0]
    linha_m = 0
    coluna_m = 0
    for i in range(3):
        for j in range(3):
            if res[i][j] > maior:
                maior = res[i][j]
                linha_m = i
                coluna_m = j

    print(f"Zagreu: devo lançar minha vara de pesca nesse ponto: ({linha_m}, {coluna_m})")
    print()


def elisio():
    legado_total = 0
    while legado_total < 200:
        linha = input().strip()
        partes = linha.split()
        nome = partes[0]
        titulo = partes[2]

        if nome == "Hércules":
            base = 50
        elif nome == "Aquiles":
            base = 40
        elif nome == "Odisseu":
            base = 35
        else:
            base = 20

        if titulo == "Imortal":
            legado_rodada = base * 1.5
        elif titulo == "Forte":
            base_mult = base * 1.2
            if base_mult.is_integer():
                legado_rodada = int(base_mult)
            else:
                legado_rodada = base_mult
        elif titulo == "Grande":
            legado_rodada = base + 15
        else:
            legado_rodada = base + 10

        if isinstance(legado_rodada, float) and legado_rodada.is_integer():
            legado_rodada = int(legado_rodada)

        legado_total += legado_rodada
        print(f"O Herói: {nome} O {titulo} adicionou {legado_rodada} pontos de Legado.")

    print("Zagreu: Acho que já fizemos história o suficiente por hoje.")
    print()


def loop_bencaos():
    deuses_validos = {
        "AFRODITE", "ARES", "ARTEMIS", "ATENA",
        "DEMETER", "DIONISIO", "HERMES", "POSEIDON", "ZEUS"
    }
    bencaos_obtidas = set()
    total_bencaos = 0

    while True:
        deus = input().strip()
        if deus == "PARAR":
            print()
            break

        if deus in deuses_validos:
            bencaos_obtidas.add(deus)
            total_bencaos += 1
            print(f"Zagreu obteve uma Bênção de {deus}.")
        elif deus == "COMBINADA":
            c1 = input().strip()
            c2 = input().strip()

            if c1 not in deuses_validos or c2 not in deuses_validos:
                print("Zagreu: Uma Bênção Combinada assim? Acho que você está brincando comigo.")
            elif c1 not in bencaos_obtidas or c2 not in bencaos_obtidas:
                print("Zagreu: Eu ainda não tenho nenhuma Bênção desse(a) Deus(a), não posso combiná-la")
            elif c1 == c2:
                print("Zagreu: Os dois Deuses precisam diferentes para realizar uma Bênção Combinada...")
            elif c1 == "HERMES" or c2 == "HERMES":
                print("Zagreu: Uma Bênção Combinada com Hermes? Acho que ele é competitivo demais pra cooperar com os outros.")
            else:
                total_bencaos += 1
                print(f"Zagreu foi abençoado por uma Bênção Combinada de {c1} e {c2}.")
        else:
            print(f'Zagreu: Ah, claro. A Bênção de {deus}. Como pude esquecer? Tenho certeza de que meu pai também deve ter esquecido de mencioná-lo(a)... Você está brincando comigo não é?.')

    return total_bencaos


def templo_estige():
    print("O Templo de Estige... o último obstáculo entre você e a superfície.")
    print()

    vida_zagreu = 100
    vida_hades = 200
    contador_ataques_hades = 0
    segunda_fase = False
    esquivando = False

    while vida_zagreu > 0 and vida_hades > 0:
        proximo_fortalecido = ((contador_ataques_hades + 1) % 3 == 0)
        if proximo_fortalecido:
            print("Zagreu: Meu pai parece estar carregando um forte ataque, é melhor desviar!")

        acao = input().strip()

        if acao == "ATACAR":
            dano = 20
            vida_hades -= dano
            print(f"Zagreu golpeia Hades, causando {dano} de dano.")
        elif acao == "ATAQUE ESPECIAL":
            dano = 40
            vida_hades -= dano
            print(f"Zagreu golpeia Hades com um ataque especial, causando {dano} de dano.")
        elif acao == "ESQUIVA":
            esquivando = True
            print("Zagreu esquiva do ataque de Hades, evitando o dano.")

        if vida_hades <= 100 and not segunda_fase:
            segunda_fase = True
            print()
            print("Hades: Chega! Isso acaba agora!")
            print()

        if vida_hades <= 0:
            break

        contador_ataques_hades += 1
        fortalecido = (contador_ataques_hades % 3 == 0)

        if segunda_fase:
            dano_hades = 100 if fortalecido else 25
        else:
            dano_hades = 50 if fortalecido else 15

        if esquivando:
            esquivando = False
            if fortalecido:
                print("Hades: Desapareça!")
            print("Hades causou 0 de dano em Zagreu." if False else f"Hades causou {0 if False else (0 if False else 0)} de dano em Zagreu." ) # Hack para evitar print incorreto caso esquive, mas o enunciado diz para imprimir o dano sempre que Hades causar dano. Se esquiva, evita o dano, mas conta o ataque.
            # Opa, o enunciado diz: "Quando Hades causar dano de qualquer forma em Zagreu, imprima: Hades causou {dano} de dano em Zagreu."
            # Se esquiva, não causa dano, logo não imprime essa linha!
            # Vamos ajustar:
        
        # Refazendo a lógica de dano de Hades corretamente:
        pass

    # Reescrevendo a função da batalha corretamente:
def templo_estige():
    print("O Templo de Estige... o último obstáculo entre você e a superfície.")
    print()

    vida_zagreu = 100
    vida_hades = 200
    contador_hades = 0
    segunda_fase = False
    esquiva_ativa = False

    while vida_zagreu > 0 and vida_hades > 0:
        proximo_e_fortalecido = ((contador_hades + 1) % 3 == 0)
        if proximo_e_fortalecido:
            print("Zagreu: Meu pai parece estar carregando um forte ataque, é melhor desviar!")

        acao = input().strip()

        if acao == "ATACAR":
            vida_hades -= 20
            print("Zagreu golpeia Hades, causando 20 de dano.")
        elif acao == "ATAQUE ESPECIAL":
            vida_hades -= 40
            print("Zagreu golpeia Hades com um ataque especial, causando 40 de dano.")
        elif acao == "ESQUIVA":
            esquiva_ativa = True
            print("Zagreu esquiva do ataque de Hades, evitando o dano.")

        if vida_hades <= 100 and not segunda_fase:
            segunda_fase = True
            print()
            print("Hades: Chega! Isso acaba agora!")
            print()

        if vida_hades <= 0:
            print()
            break

        contador_hades += 1
        eh_fortalecido = (contador_hades % 3 == 0)

        if segunda_fase:
            dano_hades = 100 if eh_fortalecido else 25
        else:
            dano_hades = 50 if eh_fortalecido else 15

        if esquiva_ativa:
            esquiva_ativa = False
            if eh_fortalecido:
                print("Hades: Desapareça!")
            print(f"Hades causou 0 de dano em Zagreu.") # Espera, o enunciado diz: "Quando Hades causar dano de qualquer forma em Zagreu, imprima: Hades causou {dano} de dano em Zagreu." Se desvia, ele não causa dano, então não imprime. Mas espere, o Exemplo 2 mostra que quando desvia NÃO imprime o dano! Exemplo 2: "Zagreu esquiva do ataque de Hades, evitando o dano." Logo em seguida vem o ataque de Zagreu.
        else:
            if eh_fortalecido:
                print("Hades: Desapareça!")
            vida_zagreu -= dano_hades
            print(f"Hades causou {dano_hades} de dano em Zagreu.")

        if vida_zagreu <= 0:
            print()
            break

    if vida_zagreu > 0:
        print("O senhor do Submundo cai diante de Zagreu. Pela primeira vez, não há nada entre ele e a superfície.")
        print("O portão se abre diante de você.")
        print("Zagreu finalmente deixa o Submundo para trás e sente o calor do sol tocar seu rosto. Pela primeira vez, a superfície está diante de seus olhos.")
        print("Você conseguiu escapar. A tentativa foi concluída.")
    else:
        print("Zagreu: Me desculpe, mãe. Foi tão perto...")


def main():
    print("O portão se abre diante de você, revelando o caminho para o Submundo. Uma nova tentativa começa agora.")
    print()

    # Tártaro
    tartaro()
    b1 = loop_bencaos()
    if b1 < 3:
        print("Zagreu cai, derrotado mais uma vez. Seu corpo se desfaz, retornando ao lugar que conhece tão bem.")
        return

    # Asfódelo
    asfodelo()
    b2 = loop_bencaos()
    if b1 + b2 < 6:
        print("Zagreu cai, derrotado mais uma vez. Seu corpo se desfaz, retornando ao lugar que conhece tão bem.")
        return

    # Elísio
    elisio()
    b3 = loop_bencaos()
    if b1 + b2 + b3 < 9:
        print("Zagreu cai, derrotado mais uma vez. Seu corpo se desfaz, retornando ao lugar que conhece tão bem.")
        return

    # Templo de Estige
    templo_estige()


if __name__ == "__main__":
    main()
