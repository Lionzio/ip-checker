# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-120b, 17/10/2026.
# Só a partir do enunciado da L3-Q6, sem nenhum código de aluno. Revise antes do merge.
import sys

banco = []
for line in sys.stdin:
    line = line.rstrip('\n')
    if line == "FIM":
        break
    nome, faccao, dano_str, intel_str, caos_str = line.split(',')
    dano = float(dano_str)
    intel = int(intel_str)
    caos = float(caos_str)

    nivel_inicial = dano + (intel * caos)
    if faccao == "Enclave":
        nivel_ameaca = nivel_inicial * 0.85
    else:
        nivel_ameaca = nivel_inicial

    banco.append((-nivel_ameaca, nome, faccao))

# cópia da lista de análise
analise = banco[:]

# lista de facções
faccoes = [t[2] for t in banco]

# ajuste dos níveis
for i, (neg_nivel, nome, faccao) in enumerate(analise):
    nivel_ameaca = -neg_nivel
    freq = faccoes.count(faccao)
    nivel_ajustado = nivel_ameaca + (nivel_ameaca * 0.05 * (freq - 1))
    analise[i] = (-nivel_ajustado, nome, faccao)

# classificação
analise.sort()

# zona prioritária
zona_prioritaria = analise[:min(3, len(analise))]

print(zona_prioritaria)
