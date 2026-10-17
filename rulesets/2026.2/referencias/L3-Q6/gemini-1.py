# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L3-Q6, sem nenhum código de aluno. Revise antes do merge.
def main():
    banco_completo = []
    
    while True:
        linha = input()
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
            
        banco_completo.append((-nivel_ameaca, nome, faccao))
        
    lista_analise = list(banco_completo)
    
    faccoes = []
    for registro in banco_completo:
        faccoes.append(registro[2])
        
    nova_lista_analise = []
    for i in range(len(lista_analise)):
        tupla = lista_analise[i]
        nivel_ameaca = -tupla[0]
        nome = tupla[1]
        faccao = tupla[2]
        
        frequencia_faccao = faccoes.count(faccao)
        
        nivel_ajustado = nivel_ameaca + (nivel_ameaca * 0.05 * (frequencia_faccao - 1))
        
        nova_lista_analise.append((-nivel_ajustado, nome, faccao))
        
    lista_analise = nova_lista_analise
    lista_analise.sort()
    
    limite = min(3, len(lista_analise))
    zona_prioritaria = lista_analise[:limite]
    
    print(zona_prioritaria)

if __name__ == "__main__":
    main()
