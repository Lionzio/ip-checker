# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L2-Q6, sem nenhum código de aluno. Revise antes do merge.
def resolver():
    ano_origem = int(input())
    ano_proibido = int(input())
    energia = int(input())
    
    ano_atual = ano_origem
    rasgo_temporal = 0
    pecas = 0
    
    print("=== WABAC: SISTEMA DE EMERGÊNCIA ===")
    print("Alvo: Ano 2026 | Peças Necessárias: 3")
    print("Sherman, mantenha as mãos longe dos botões! Iniciando saltos...")
    
    primeiro_salto_feito = False
    motivo_parada = None
    
    while True:
        # Checar condições de parada antes de ler ação
        # 1. Paradoxo das Duplicatas
        if ano_atual == ano_proibido or (primeiro_salto_feito and ano_atual == ano_origem):
            motivo_parada = "PARADOXO"
            break
        # 2. Apagão Temporal
        if energia <= 0:
            motivo_parada = "APAGAO"
            break
        # 3. Colapso Dimensional
        if rasgo_temporal >= 100:
            motivo_parada = "COLAPSO"
            break
        # 5. Missão Cumprida
        if pecas >= 3 and ano_atual >= 2026:
            motivo_parada = "SUCESSO"
            break
            
        try:
            acao = input()
        except EOFError:
            break
            
        # 4. Comando de Abortar (pode vir como ação)
        if acao == "ABORTAR":
            motivo_parada = "ABORTAR"
            break
            
        if acao == "SALTAR":
            anos_salto = int(input())
            custo_energia = int(input())
            
            ano_atual += anos_salto
            energia -= custo_energia
            if energia < 0:
                energia = 0
            rasgo_temporal += 10
            if rasgo_temporal > 100:
                rasgo_temporal = 100
                
            primeiro_salto_feito = True
            
            # Checar condições de parada imediatamente após a ação
            if ano_atual == ano_proibido or (primeiro_salto_feito and ano_atual == ano_origem):
                motivo_parada = "PARADOXO"
                break
            if energia <= 0:
                motivo_parada = "APAGAO"
                break
            if rasgo_temporal >= 100:
                motivo_parada = "COLAPSO"
                break
            if pecas >= 3 and ano_atual >= 2026:
                motivo_parada = "SUCESSO"
                break
                
            print(f"WABAC saltou para o ano {ano_atual}!")
            print(f"Energia restante: {energia} | Rasgo Temporal: {rasgo_temporal}%")
            
        elif acao == "CONSERTAR":
            dificuldade = int(input())
            esforco_sherman = int(input())
            
            sucesso_conserto = esforco_sherman >= dificuldade
            if sucesso_conserto:
                pecas += 1
                energia -= 10
            else:
                energia -= 15
                rasgo_temporal += 20
                
            if energia < 0:
                energia = 0
            if rasgo_temporal > 100:
                rasgo_temporal = 100
                
            # Checar condições de parada
            if ano_atual == ano_proibido or (primeiro_salto_feito and ano_atual == ano_origem):
                motivo_parada = "PARADOXO"
                break
            if energia <= 0:
                motivo_parada = "APAGAO"
                break
            if rasgo_temporal >= 100:
                motivo_parada = "COLAPSO"
                break
            if pecas >= 3 and ano_atual >= 2026:
                motivo_parada = "SUCESSO"
                break
                
            if sucesso_conserto:
                print('Sherman: "Consegui, Mr. Peabody! Encontrei uma peça de calibragem!"')
                print(f"Peças coletadas: {pecas}/3 | Energia: {energia}")
            else:
                print('Mr. Peabody: "Tenha mais cuidado, Sherman! Essa falha desestabilizou o tempo!"')
                print(f"Energia: {energia} | Rasgo Temporal: {rasgo_temporal}%")
                
        elif acao == "AULA DE HISTÓRIA":
            energia += 25
            rasgo_temporal += 15
            if rasgo_temporal > 100:
                rasgo_temporal = 100
                
            # Checar condições de parada
            if ano_atual == ano_proibido or (primeiro_salto_feito and ano_atual == ano_origem):
                motivo_parada = "PARADOXO"
                break
            if energia <= 0:
                motivo_parada = "APAGAO"
                break
            if rasgo_temporal >= 100:
                motivo_parada = "COLAPSO"
                break
            if pecas >= 3 and ano_atual >= 2026:
                motivo_parada = "SUCESSO"
                break
                
            print('Mr. Peabody: "Como disse Galileu Galilei, a matemática é a linguagem com a qual Deus escreveu o universo."')
            print(f"Energia recarregada para {energia}!")

    # Se saiu do loop sem definir o motivo (ex: EOF), checa novamente as condições na ordem correta
    if motivo_parada is None:
        if ano_atual == ano_proibido or (primeiro_salto_feito and ano_atual == ano_origem):
            motivo_parada = "PARADOXO"
        elif energia <= 0:
            motivo_parada = "APAGAO"
        elif rasgo_temporal >= 100:
            motivo_parada = "COLAPSO"
        elif pecas >= 3 and ano_atual >= 2026:
            motivo_parada = "SUCESSO"
        else:
            motivo_parada = "ABORTAR"

    # Imprimir mensagem final
    if motivo_parada == "PARADOXO":
        print(f"ALERTA CRÍTICO: Peabody encontrou sua própria versão no ano {ano_atual}!")
        print("O continuum espaço-tempo ruiu em uma espiral paradoxal.")
    elif motivo_parada == "APAGAO":
        print("A WABAC desligou completamente por falta de energia.")
        print("Peabody e Sherman estão vagando sem rumo pela linha do tempo...")
    elif motivo_parada == "COLAPSO":
        print("O rasgo temporal atingiu massa crítica!")
        print("O universo foi engolido por um buraco negro sobre a cidade de Nova York.")
    elif motivo_parada == "ABORTAR":
        print("Mr. Peabody acionou o protocolo de parada manual.")
        print("A viagem foi cancelada antes de sua conclusão.")
    elif motivo_parada == "SUCESSO":
        print(f"A WABAC emergiu com sucesso no ano de {ano_atual}!")
        print("Com as 3 peças coletadas, Mr. Peabody selou o rasgo temporal e salvou o presente!")

resolver()
