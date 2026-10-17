# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-20b, 17/10/2026.
# Só a partir do enunciado da L2-Q5, sem nenhum código de aluno. Revise antes do merge.
import sys

def main():
    try:
        qnt_ataques = int(input())
    except:
        return

    print("Quando percebi que contara oito mortes, senti o peso da minha própria lenda")

    if qnt_ataques == 0:
        print("Até logo, velho amigo... É bom saber que finalmente posso respirar fundo e apenas viver o dia de hoje.")
        return

    desfecho = False
    for _ in range(qnt_ataques):
        print("Preciso encontrar esse mapa a qualquer custo, nem que seja a última coisa que eu faça com esta vida!")
        companion = input()
        if companion == "cao perrito":
            print("Olha só... de todas as criaturas do mundo, justo você tinha que decidir me seguir com esse rabo abanando?")
            try:
                N = int(input())
            except:
                N = 0
            all_div3 = True
            for _ in range(N):
                try:
                    num = int(input())
                except:
                    num = 0
                if num % 3 != 0:
                    all_div3 = False
            if all_div3:
                print("Bom trabalho, meu garoto! Quem diria que um cãozinho tão pequeno seria o grande herói do dia?")
                desfecho = True
                break
        elif companion == "kitty patamansa":
            print("Kitty... Olhar para você de novo só me faz lembrar que, entre todas as minhas nove vidas, o meu maior erro foi ter deixado você esperando.")
            item = input()
            if item == "chapeu do gato" or item == "bota do gato":
                print("Impressionante, Kitty... Sempre soube que você era rápida, mas admito que nada fica melhor nas mãos da melhor ladra de Tão Tão Distante do que um presente para mim.")
                desfecho = True
                break
        else:
            while True:
                frase = input()
                if "Desfecho" in frase:
                    desfecho = True
                    break
                if "Morte" in frase:
                    break

    if desfecho:
        frase_gato = input()
        if "coragem" in frase_gato.lower():
            print("Parece que essa família de ursos e sua cachinhos acabam de provar do verdadeiro felino de botas!")
            print("A verdadeira vitória não está em vencer a morte, mas em encará-la de frente e escolher lutar por cada segundo desta vida!")
        else:
            print("Pode levar minha espada e meu chapéu... Eu lutei até o fim, mas hoje a lenda finalmente descansa.")
    else:
        print("Pode levar minha espada e meu chapéu... Eu lutei até o fim, mas hoje a lenda finalmente descansa.")

if __name__ == "__main__":
    main()
