# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L3-Q8, sem nenhum código de aluno. Revise antes do merge.
import sys


def resolver():
    linhas_input = sys.stdin.read().splitlines()
    if not linhas_input:
        return
    iterador_input = iter(linhas_input)

    # --- FASE 1 ---
    N_fase1 = int(next(iterador_input))
    matriz_cena = []
    for _ in range(N_fase1):
        linha = [item.strip() for item in next(iterador_input).split(",")]
        matriz_cena.append(linha)

    l_inicio, l_fim, c_inicio, c_fim = map(int, next(iterador_input).split())

    sub_matriz = []
    qtd_sangue = 0
    qtd_arma = 0
    tem_smiley = False

    for i in range(l_inicio, l_fim):
        linha_sub = []
        for j in range(c_inicio, c_fim):
            item = matriz_cena[i][j]
            linha_sub.append(item)
            if item == "Sangue":
                qtd_sangue += 1
            elif item == "Arma":
                qtd_arma += 1
            elif item == "Smiley":
                tem_smiley = True
        sub_matriz.append(linha_sub)

    print("--- FASE 1: A VARREDURA ---")
    print("Lisbon: Jane, focamos as buscas no quadrante delimitado.")
    for linha in sub_matriz:
        print(linha)
    smiley_str = "Sim" if tem_smiley else "Nao"
    print(
        f"Evidencias encontradas: Sangue ({qtd_sangue}), Arma ({qtd_arma}). Smiley ({smiley_str})"
    )
    print()

    # --- Fase 2 ---
    N_f2, M_f2 = map(int, next(iterador_input).split())
    matriz_evidencias = []
    for _ in range(N_f2):
        matriz_evidencias.append(list(map(int, next(iterador_input).split())))

    T = int(next(iterador_input))

    matriz_binaria = []
    for i in range(N_f2):
        linha_bin = []
        for j in range(M_f2):
            if matriz_evidencias[i][j] >= T:
                linha_bin.append(1)
            else:
                linha_bin.append(0)
        matriz_binaria.append(linha_bin)

    assinatura = [[1, 1, 0, 1, 1], [1, 0, 0, 0, 1], [0, 1, 1, 1, 0]]
    assinatura_encontrada = False
    coord_encontrada = (-1, -1)

    for i in range(N_f2 - 3 + 1):
        if assinatura_encontrada:
            break
        for j in range(M_f2 - 5 + 1):
            match = True
            for ai in range(3):
                for aj in range(5):
                    if matriz_binaria[i + ai][j + aj] != assinatura[ai][aj]:
                        match = False
                        break
                if not match:
                    break
            if match:
                assinatura_encontrada = True
                coord_encontrada = (i, j)
                break

    print("--- FASE 2: A MATRIZ DE EVIDÊNCIAS ---")
    print(
        "Patrick Jane: Às vezes, a verdade está escondida bem diante dos nossos olhos."
    )
    for linha in matriz_binaria:
        print(" ".join(map(str, linha)))

    red_john = tem_smiley or assinatura_encontrada

    if not red_john:
        print("Patrick Jane: Nada aqui parece familiar.")
    else:
        print("Patrick Jane: Eu conheço esse sorriso.")
        print("RED JOHN DEIXOU UMA ASSINATURA!")
        print(
            f"ASSINATURA ENCONTRADA EM [{coord_encontrada[0]}][{coord_encontrada[1]}]"
        )
    print()

    # --- FASE 3 ---
    if red_john:
        try:
            linha_nums = next(iterador_input)
            nums = list(map(int, linha_nums.split()))
        except StopIteration:
            nums = []

        alfabeto = "abcdefghijklmnopqrstuvwxyz "

        mensagem_chars = [
            alfabeto[(x // 2) % 27] if x % 2 == 0 else alfabeto[(x * 3 + 1) % 27]
            for x in nums
        ]
        mensagem = "".join(mensagem_chars)

        print("--- FASE 3: A MENSAGEM ---")
        print(f'Mensagem decodificada: "{mensagem}"')
        print(
            "Jane: Ele acha que é mais esperto que eu. Nós vamos pegá-lo."
        )
    else:
        try:
            nota_cifrada = next(iterador_input)
        except StopIteration:
            nota_cifrada = ""

        invertida = nota_cifrada[::-1]
        pares = [invertida[i] for i in range(0, len(invertida), 2)]
        transformados = [
            c.lower() if c.isupper() else (c.upper() if c.islower() else c)
            for c in pares
        ]
        mensagem_decodificada = "".join(transformados)

        qtd_j = mensagem_decodificada.count("j") + mensagem_decodificada.count(
            "J"
        )

        print("--- FASE 3: O CÓDIGO ---")
        print("Patrick Jane: Vamos ver o que ele quis dizer dessa vez.")
        print("MENSAGEM DECODIFICADA!")
        print(f"Patrick Jane: '{mensagem_decodificada}'...")
        print("Patrick Jane: Esse caso acabou de dar uma reviravolta interessante.")
        print(
            f"Grau de Obsessão: {qtd_j} aparição(ões) da letra J na mensagem."
        )
        print("--- CASO ENCERRADO (por enquanto...) ---")


if __name__ == "__main__":
    resolver()
