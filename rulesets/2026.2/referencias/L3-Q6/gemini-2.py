# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L3-Q6, sem nenhum código de aluno. Revise antes do merge.
import sys


def main():
    banco_completo = []
    lista_faccoes = []

    for linha in sys.stdin:
        linha = linha.strip()
        if not linha:
            continue
        if linha == "FIM":
            break

        partes = linha.split(",")
        nome = partes[0]
        faccao = partes[1]
        dano_base = float(partes[2])
        inteligencia = int(partes[3])
        fator_caos = float(partes[4])

        nivel_inicial = dano_base + (inteligencia * fator_caos)

        if faccao == "Enclave":
            nivel_ameaca = nivel_inicial - (nivel_inicial * 0.15)
        else:
            nivel_ameaca = nivel_inicial

        tupla_registro = (-nivel_ameaca, nome, faccao)
        banco_completo.append(tupla_registro)
        lista_faccoes.append(faccao)

    lista_analise = list(banco_completo)

    for i in range(len(lista_analise)):
        tupla_atual = lista_analise[i]
        nivel_negativo, nome, faccao = tupla_atual
        nivel_ameaca = -nivel_negativo

        frequencia_faccao = lista_faccoes.count(faccao)

        nivel_ajustado = nivel_ameaca + (
            nivel_ameaca * 0.05 * (frequencia_faccao - 1)
        )

        lista_analise[i] = (-nivel_ajustado, nome, faccao)

    lista_analise.sort()

    limite = min(3, len(lista_analise))
    zona_prioritaria = lista_analise[:limite]

    print(zona_prioritaria)


if __name__ == "__main__":
    main()
