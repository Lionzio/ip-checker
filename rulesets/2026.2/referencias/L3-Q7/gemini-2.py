# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L3-Q7, sem nenhum código de aluno. Revise antes do merge.
def main():
    herois = []
    
    while True:
        linha = input().strip()
        if linha == "FIM":
            break
        partes = [p.strip() for p in linha.split("-")]
        nome = partes[0]
        forca = int(partes[1])
        resistencia = int(partes[2])
        velocidade = int(partes[3])
        inteligencia = int(partes[4])
        experiencia = int(partes[5])
        
        herois.append({
            "nome": nome,
            "Força": forca,
            "Resistência": resistencia,
            "Velocidade": velocidade,
            "Inteligência": inteligencia,
            "Experiência": experiencia
        })
        
    num_ameacas = int(input().strip())
    
    print("========================================")
    print("GDA - HERO DISPATCH SYSTEM")
    print("========================================")
    print("[ROBOT] Sistema de despacho iniciado.")
    print(f"[ROBOT] {len(herois)} heróis disponíveis.")
    
    for _ in range(num_ameacas):
        linha_ameaca = input().strip()
        partes_am = [p.strip() for p in linha_ameaca.split("-")]
        nome_ameaca = partes_am[0]
        nivel = int(partes_am[1])
        prioridade = partes_am[2]
        
        print("========================================")
        print("NOVA AMEAÇA DETECTADA")
        print("========================================")
        print(f"AMEAÇA: {nome_ameaca}")
        print(f"NÍVEL DE DIFICULDADE: {nivel}")
        print(f"PRIORIDADE: {prioridade}")
        print()
        print("[ROBOT] Analisando heróis disponíveis...")
        print("[ROBOT] Calculando compatibilidade...")
        print("[ROBOT] Análise concluída.")
        
        ranking = []
        for h in herois:
            soma_total = h["Força"] + h["Resistência"] + h["Velocidade"] + h["Inteligência"] + h["Experiência"]
            pontuacao = soma_total + h[prioridade]
            ranking.append({
                "nome": h["nome"],
                "pontuacao": pontuacao,
                "atributo_prioritario": h[prioridade],
                "indice_original": herois.index(h)
            })
            
        n = len(ranking)
        for i in range(n):
            for j in range(0, n - i - 1):
                h1 = ranking[j]
                h2 = ranking[j + 1]
                
                trocar = False
                if h1["pontuacao"] < h2["pontuacao"]:
                    trocar = True
                elif h1["pontuacao"] == h2["pontuacao"]:
                    if h1["atributo_prioritario"] < h2["atributo_prioritario"]:
                        trocar = True
                    elif h1["atributo_prioritario"] == h2["atributo_prioritario"]:
                        if h1["indice_original"] > h2["indice_original"]:
                            trocar = True
                            
                if trocar:
                    ranking[j], ranking[j + 1] = ranking[j + 1], ranking[j]
                    
        print("========================================")
        print("RANKING DE HERÓIS")
        print("========================================")
        for idx, h in enumerate(ranking, 1):
            print(f"{idx}. {h['nome']} - {h['pontuacao']} pontos")
            
        print("----------------------------------------")
        if 1 <= nivel <= 30:
            classificacao = "SIMPLES"
            necessarios = 1
        elif 31 <= nivel <= 70:
            classificacao = "MODERADA"
            necessarios = 2
        else:
            classificacao = "CRÍTICA"
            necessarios = 3
            
        print(f"[ROBOT] Ameaça {classificacao}.")
        print(f"[ROBOT] {necessarios} herói(s) serão despachados.")
        
        disponiveis = len(herois)
        if necessarios > disponiveis:
            print()
            print("[ROBOT] ALERTA!")
            print(f"[ROBOT] São necessários {necessarios} heróis,")
            print(f"[ROBOT] mas apenas {disponiveis} estão disponíveis.")
            print("[ROBOT] Despachando todos os heróis disponíveis.")
            equipe = ranking[:disponiveis]
        else:
            print("[CECIL] Equipe selecionada para a missão.")
            equipe = ranking[:necessarios]
            
        print("EQUIPE DESPACHADA:")
        for h in equipe:
            print(f"> {h['nome']}")
            
        print("========================================")

if __name__ == "__main__":
    main()
