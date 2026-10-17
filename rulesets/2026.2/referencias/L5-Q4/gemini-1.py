# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L5-Q4, sem nenhum código de aluno. Revise antes do merge.
def main():
    frase = input()
    consulta = input()

    variacoes = {
        "a": "aáàâãäAÁÀÂÃÄ",
        "e": "eéèêëEÉÈÊË",
        "i": "iíìîïIÍÌÎÏ",
        "o": "oóòôõöOÓÒÔÕÖ",
        "u": "uúùûüUÚÙÛÜ",
    }

    base_map = {}
    for letra_base, disfarces in variacoes.items():
        for d in disfarces:
            base_map[d] = letra_base

    censo_cont = {}
    censo_ordem = []

    livro = {}

    for char in frase:
        if not char.isalpha():
            continue

        base = base_map.get(char, char.lower())

        if base not in censo_cont:
            censo_cont[base] = 0
            censo_ordem.append(base)
        censo_cont[base] += 1

        if base not in livro:
            livro[base] = {}
        if char not in livro[base]:
            livro[base][char] = 0
        livro[base][char] += 1

    itens = [(b, censo_cont[b]) for b in censo_ordem]

    for i in range(len(itens)):
        for j in range(i + 1, len(itens)):
            if itens[j][1] > itens[i][1]:
                itens[i], itens[j] = itens[j], itens[i]

    saida_censo = []
    for base, qtd in itens:
        saida_censo.append(f"{qtd}{base}")
    print(" ".join(saida_censo))

    total = sum(livro[consulta].values())
    qtd_var = len(livro[consulta])

    fav_char = None
    fav_qtd = -1

    for char in frase:
        if char in livro[consulta]:
            q = livro[consulta][char]
            if q > fav_qtd:
                fav_qtd = q
                fav_char = char

    print(f"Total de ocorrências: {total}")
    print(f"Quantidade de variações: {qtd_var}")
    print(f"Variação mais frequente: {fav_char} ({fav_qtd})")


if __name__ == "__main__":
    main()
