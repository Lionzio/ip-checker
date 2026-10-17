# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L3-Q8, sem nenhum código de aluno. Revise antes do merge.
import sys


def resolver():
    linhas = sys.stdin.read().splitlines()
    if not linhas:
        return
    idx = 0

    # Fase 1
    N_f1 = int(linhas[idx])
    idx += 1
    matriz_cena = []
    for _ in range(N_f1):
        itens = [x.strip() for x in linhas[idx].split(",")]
        idx += 1
        matriz_cena.append(itens)

    l_ini, l_fim, c_ini, c_fim = map(int, linhas[idx].split())
    idx += 1

    sub_matriz = []
    qtd_sangue = 0
    qtd_arma = 0
    tem_smiley = False

    for r in range(l_ini, l_fim):
        linha_sub = []
        for c in range(c_ini, c_fim):
            val = matriz_cena[r][c]
            linha_sub.append(val)
            if val == "Sangue":
                qtd_sangue += 1
            elif val == "Arma":
                qtd_arma += 1
            elif val == "Smiley":
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

    # Fase 2
    N_f2, M_f2 = map(int, linhas[idx].split())
    idx += 1
    matriz_evid = []
    for _ in range(N_f2):
        row = list(map(int, linhas[idx].split()))
        idx += 1
        matriz_evid.append(row)

    T = int(linhas[idx])
    idx += 1

    matriz_bin = []
    for r in range(N_f2):
        bin_row = []
        for c in range(M_f2):
            if matriz_evid[r][c] >= T:
                bin_row.append(1)
            else:
                bin_row.append(0)
        matriz_bin.append(bin_row)

    print("--- FASE 2: A MATRIZ DE EVIDÊNCIAS ---")
    print("Patrick Jane: Às vezes, a verdade está escondida bem diante dos nossos olhos.")
    for bin_row in matriz_bin:
        print(" ".join(map(str, bin_row)))

    assinatura = [[1, 1, 0, 1, 1], [1, 0, 0, 0, 1], [0, 1, 1, 1, 0]]
    assinatura_encontrada = False
    coord_r, coord_c = -1, -1

    for r in range(N_f2 - 3 + 1):
        if assinatura_encontrada:
            break
        for c in range(M_f2 - 5 + 1):
            match = True
            for i in range(3):
                for j in range(5):
                    if matriz_bin[r + i][c + j] != assinatura[i][j]:
                        match = False
                        break
                if not match:
                    break
            if match:
                assinatura_encontrada = True
                coord_r, coord_c = r, c
                break

    if assinatura_encontrada:
        print("Patrick Jane: Eu conheço esse sorriso.")
        print("RED JOHN DEIXOU UMA ASSINATURA!")
        print(f"ASSINATURA ENCONTRADA EM [{coord_r}][{coord_c}]")
    else:
        print("Patrick Jane: Nada aqui parece familiar.")
    print()

    red_john = tem_smiley or assinatura_encontrada

    # Fase 3
    if red_john:
        print("--- FASE 3: A MENSAGEM ---")
        numeros = list(map(int, linhas[idx].split()))
        idx += 1
        alfabeto = "abcdefghijklmnopqrstuvwxyz "

        indices = [
            (x // 2) % 27 if x % 2 == 0 else (x * 3 + 1) % 27 for x in numeros
        ]
        mensagem = "".join(alfabeto[i] for i in indices)

        print(f'Mensagem decodificada: "{mensagem}"')
        print("Jane: Ele acha que é mais esperto que eu. Nós vamos pegá-lo.")
    else:
        print("--- FASE 3: O CÓDIGO ---")
        nota = linhas[idx]
        idx += 1

        invertida = nota[::-1]
        fatiada = invertida[::2]
        decodificada = "".join(
            c.lower() if c.isupper() else (c.upper() if c.islower() else c)
            for c in fatiada
        )

        qtd_j = decodificada.count("j") + decodificada.count("J")

        print("Patrick Jane: Vamos ver o que ele quis dizer dessa vez.")
        print("MENSAGEM DECODIFICADA!")
        print(f"Patrick Jane: '{decodificada}'...")
        print("Patrick Jane: Esse caso acabou de dar uma reviravolta interessante.")
        print(f"Grau de Obsessão: {qtd_j} aparição(ões) da letra J na mensagem.")
        print("--- CASO ENCERRADO (por enquanto...) ---")


if __name__ == "__main__":
    resolver()
