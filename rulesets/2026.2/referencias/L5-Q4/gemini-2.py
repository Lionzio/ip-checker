# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L5-Q4, sem nenhum código de aluno. Revise antes do merge.
frase = input()
consulta = input()

variacoes = {
    "a": "aáàâãäAÁÀÂÃÄ",
    "e": "eéèêëEÉÈÊË",
    "i": "iíìîïIÍÌÎÏ",
    "o": "oóòôõöOÓÒÔÕÖ",
    "u": "uúùûüUÚÙÛÜ",
}

# Mapear cada caractere acentuado/maiúsculo para sua base minúscula
mapa_base = {}
for base, vars_str in variacoes.items():
    for v in vars_str:
        mapa_base[v] = base

# Adicionar consoantes e suas maiúsculas
for c in "bcdfghjklmnpqrstvwxyz":
    mapa_base[c] = c
    mapa_base[c.upper()] = c

contagem_censo = {}
ordem_aparecimento = []
livro_disfarces = {}

for char in frase:
    if char in mapa_base:
        base = mapa_base[char]

        # Para o censo e ordem de aparição das bases
        if base not in contagem_censo:
            contagem_censo[base] = 0
            ordem_aparecimento.append(base)
        contagem_censo[base] += 1

        # Para o livro de disfarces
        if base not in livro_disfarces:
            livro_disfarces[base] = {}
        if char not in livro_disfarces[base]:
            livro_disfarces[base][char] = 0
        livro_disfarces[base][char] += 1

# Ordenação manual (bubble sort) para o censo
# Critérios: maior contagem primeiro; em caso de empate, quem apareceu primeiro na frase
bases_ordenadas = list(ordem_aparecimento)
n = len(bases_ordenadas)
for i in range(n):
    for j in range(0, n - i - 1):
        b1 = bases_ordenadas[j]
        b2 = bases_ordenadas[j + 1]
        c1 = contagem_censo[b1]
        c2 = contagem_censo[b2]

        # Queremos c1 < c2 para trocar, pois queremos decrescente
        if c1 < c2:
            bases_ordenadas[j], bases_ordenadas[j + 1] = b2, b1
        elif c1 == c2:
            # Se empatar, o que apareceu primeiro na frase fica antes.
            # Como ordem_aparecimento guarda na ordem que surgiram,
            # verificamos seus índices em ordem_aparecimento.
            idx1 = ordem_aparecimento.index(b1)
            idx2 = ordem_aparecimento.index(b2)
            if idx1 > idx2:
                bases_ordenadas[j], bases_ordenadas[j + 1] = b2, b1

# Parte 1: Censo
censo_str = " ".join(
    f"{contagem_censo[b]}{b}" for b in bases_ordenadas
)
print(censo_str)

# Parte 2: O Interrogatório
total_ocorr = contagem_censo[consulta]
qtd_var = len(livro_disfarces[consulta])

# Achar a variação mais frequente (mantendo ordem de aparição para desempate)
disfarces_do_animago = livro_disfarces[consulta]
melhor_var = None
max_freq = -1

# Para garantir a ordem de aparição na frase para o desempate:
# iteramos novamente pela frase para pegar a ordem exata dos disfarces
disfarces_vistos = []
for char in frase:
    if mapa_base.get(char) == consulta:
        if char not in disfarces_vistos:
            disfarces_vistos.append(char)

for d in disfarces_vistos:
    freq = disfarces_do_animago[d]
    if freq > max_freq:
        max_freq = freq
        melhor_var = d

print(f"Total de ocorrências: {total_ocorr}")
print(f"Quantidade de variações: {qtd_var}")
print(f"Variação mais frequente: {melhor_var} ({max_freq})")
