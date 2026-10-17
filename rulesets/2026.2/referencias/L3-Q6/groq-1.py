# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-120b, 17/10/2026.
# Só a partir do enunciado da L3-Q6, sem nenhum código de aluno. Revise antes do merge.
import sys

def read_input():
    banco = []
    for line in sys.stdin:
        line = line.rstrip('\n')
        if line == "FIM":
            break
        nome, faccao, dano_base, inteligencia, fator_caos = line.split(',')
        dano_base = float(dano_base)
        inteligencia = int(inteligencia)
        fator_caos = float(fator_caos)

        nivel_inicial = dano_base + (inteligencia * fator_caos)
        if faccao == "Enclave":
            nivel_ameaca = nivel_inicial * 0.85  # 15% penalty
        else:
            nivel_ameaca = nivel_inicial

        banco.append((-nivel_ameaca, nome, faccao))
    return banco

def main():
    banco = read_input()
    # cópia da lista para análise
    analise = banco[:]

    # lista de facções na ordem original
    faccoes = [t[2] for t in banco]

    # ajuste dos níveis conforme frequência
    for i, (neg_nivel, nome, faccao) in enumerate(analise):
        nivel_ameaca = -neg_nivel  # valor positivo
        freq = faccoes.count(faccao)
        nivel_ajustado = nivel_ameaca + (nivel_ameaca * 0.05 * (freq - 1))
        analise[i] = (-nivel_ajustado, nome, faccao)

    # classificação
    analise.sort()

    # zona prioritária (até 3 ameaças)
    zona_prioritaria = analise[:3]

    print(zona_prioritaria)

if __name__ == "__main__":
    main()
