# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L2-Q2, sem nenhum código de aluno. Revise antes do merge.
def main():
    perigo = 100
    print("Os pinguins começaram sua fuga. Operação: sair de Mônaco vivos!")
    
    rodadas = int(input())
    
    for _ in range(rodadas):
        if perigo <= 0:
            # Se já zerou, as próximas rodadas ainda leem entrada mas não mudam fluxo ou podem ser lidas normalmente
            # O enunciado diz "caso ainda não tenha zerado o nível de perigo, será recebida uma ação"
            # Vamos garantir a leitura caso o loop continue, mas normalmente perigo <= 0 encerra.
            # Porém, para garantir robustez com a quantidade de inputs fornecidos:
            pass

        acao = input()
        
        if acao == "CHANTEL DUBOUIS":
            print("Parece que a Capitã Dubouis ganhou uma ajudinha extra na caçada... Como se ela precisasse.")
            ajuda = input()
            if ajuda == "helicóptero":
                print("Pendurada em um helicóptero, Dubouis se aproxima cada vez mais dos fugitivos!")
                perigo += 15
            elif ajuda == "rastrear":
                print("Dubouis encontrou os rastros dos animais. Infelizmente, despistar essa mulher não estava no plano.")
                perigo += 20
            elif ajuda == "SCOOTER":
                print("ELA PEGOU A LENDÁRIA SCOOTER! OS PINGUINS REALMENTE TÊM ALGUMA CHANCE?!")
                perigo += 35
            elif ajuda == "Non, je ne regrette rien":
                print("INACREDITÁVEL! A VOZ ANGELICAL DE DUBOIS REANIMOU TODA A EQUIPE! ISSO É PERMITIDO?!")
                perigo += 100
            else:
                print("Um dos capangas encontrou uma pista dos animais. Pequena pista, enorme problema.")
                perigo += 5
                
        elif acao == "kowalski":
            print("Kowalski teve uma ideia! Por algum milagre, ela realmente funcionou e atrasou a caçadora.")
            perigo -= 30
            
        elif acao == "capitão":
            print("Após uma troca de golpes com Dubouis, o Capitão conseguiu atrasá-la. Liderança também envolve pancadaria.")
            perigo -= 40
            
        elif acao == "RICO":
            print("Rico sacou uma bomba de procedência extremamente duvidosa e acertou em cheio! Clássico Rico.")
            perigo -= 50
            
        else:
            print("Parece que o Recruta vai tentar ajudar na fuga... Que os céus protejam essa operação.")
            recruta = input()
            if recruta == "sucesso":
                print("ELE CONSEGUIU! A fofura do Recruta distraiu os guardas de Dubouis. Uma arma verdadeiramente devastadora.")
                perigo -= 15
            else:
                print("Ele tentou... mas deixou um rastro enorme para os guardas. Pelo menos a intenção foi boa.")
                perigo += 10

    if perigo <= 0:
        print("ELES CONSEGUIRAM! Deixaram a grandiosa CHANTEL DUBOUIS para trás e seguiram rumo a Madagascar!")
    else:
        print("Os pinguins não tiveram chance... A maior caçadora de animais de Mônaco é simplesmente IMPLACÁVEL!")

if __name__ == "__main__":
    main()
