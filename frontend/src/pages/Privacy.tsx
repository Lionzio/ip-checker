import { Link } from "react-router";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { PAGE_TITLES } from "../labels";

/**
 * Aviso de privacidade (S19-02; Q-16, Q-19 d, NFR-11). Descreve o que o sistema faz de fato; se os
 * dados guardados ou enviados a terceiros mudarem, este texto muda junto (DoD, seção 8).
 */
export function Privacy() {
  useDocumentTitle(PAGE_TITLES.privacy);
  return (
    <article className="mx-auto flex max-w-3xl flex-col gap-4 py-6 leading-relaxed">
      <h2 className="text-xl font-semibold">Aviso de privacidade</h2>
      <p>
        O IP-Checker é de uso exclusivo da equipe da disciplina de Introdução à Programação. Este aviso
        explica quais dados ele guarda, para quê, quem os vê e o que sai do servidor.
      </p>

      <h3 className="text-lg font-semibold">Dados da sua conta</h3>
      <ul className="list-disc pl-6">
        <li>
          Nome, e-mail institucional, curso e tratamento (masculino, feminino ou neutro), informados no
          registro e editáveis no perfil.
        </li>
        <li>
          A senha, guardada só como resumo criptográfico (Argon2id): ninguém, nem a equipe técnica,
          consegue lê-la. Quem entra pelo Google não tem senha guardada; fica só o identificador da
          conta Google.
        </li>
        <li>Cargo, situação da conta, data do pedido e quem o aprovou ou recusou.</li>
        <li>
          Para a chefia e o desenvolvedor, os tokens de importação da extensão do Dikastis, guardados
          só como resumo criptográfico, com o nome dado a cada um e as datas de criação, de uso e de
          revogação. O catálogo das listas (enunciados e casos de exemplo do Dikastis) não tem dados
          pessoais.
        </li>
      </ul>
      <p>
        Esses dados servem para dar acesso só à equipe, aprovar os cadastros e montar a apresentação
        do feedback. Nome, e-mail, curso, cargo e situação aparecem na tela de gerenciamento, que só o
        desenvolvedor, os professores e os monitores-chefe acessam. O tratamento só você vê, e ele é
        usado apenas para escrever o feedback.
      </p>
      <p>
        Cada aprovação, recusa, mudança de cargo, remoção e reativação entra num registro de ações, com o
        nome e o cargo de quem agiu e de quem recebeu a ação, a mudança e a data. Só o desenvolvedor e os
        professores o veem, ninguém o edita, e cada ação é apagada depois de 12 meses.
      </p>

      <h3 className="text-lg font-semibold">Código dos alunos</h3>
      <p>
        O código verificado, comparado no painel de plágio ou usado no feedback é analisado e
        descartado: não vai para o banco, para o disco nem para os logs, e nunca é executado. Os
        indícios de uso de IA, quando ligados, são calculados na hora a partir do mesmo código, só a
        equipe os vê, e também não são guardados. O que está no editor, com o nome do aluno e a
        anotação, fica só nesta aba do seu navegador, para sobreviver a um recarregamento, e some
        quando a aba fecha ou quando você sai da conta; nada disso vai ao servidor.
      </p>

      <h3 className="text-lg font-semibold">Estatísticas de uso</h3>
      <p>
        Cada verificação gera um registro anônimo: período, lista, versão das regras, resultado, as
        regras apontadas e o tempo de análise. Ele não guarda o código, a conta, o nome de ninguém nem
        o IP. Os professores consultam só contagens agregadas (regras mais apontadas, erros de sintaxe e
        volume por semana), e os registros são apagados depois de 12 meses.
      </p>
      <p>
        Para medir quanto a equipe usa a ferramenta (um dos critérios do piloto), o sistema guarda, para
        cada conta, em quais listas de cada período ela já verificou algum código: só a lista e o
        período, sem data, código nem resultado. Os professores veem só a porcentagem da equipe que
        usou cada lista, nunca quem, e o registro some junto com a conta.
      </p>

      <h3 className="text-lg font-semibold">Feedback</h3>
      <p>
        O texto do feedback é montado por modelos no próprio servidor, sem IA, e nada sai dele. Só
        quando você clica em Aprimorar com IA vão a um provedor de IA o código sem os comentários e sem
        as docstrings, a anotação, o resultado da verificação e o texto sem IA. Antes do envio, o nome
        do aluno é trocado por [ALUNO], e e-mails, CPFs e números com 8 ou mais dígitos (como
        matrículas) são trocados por marcas; o seu nome e o seu cargo não vão. Os provedores usados
        são de planos gratuitos, que podem usar o que recebem para treinar modelos (decisão do
        autor, Q-16).
      </p>

      <h3 className="text-lg font-semibold">Sessão, e-mail e registros técnicos</h3>
      <ul className="list-disc pl-6">
        <li>
          A sessão fica num cookie que a página não consegue ler; o servidor guarda só o resumo do
          identificador. Ela termina depois de 12 horas sem uso, em no máximo 7 dias, ao sair, ao
          trocar a senha, ao mudar de cargo ou ao ser removido da equipe.
        </li>
        <li>O link de verificação do registro é enviado ao seu e-mail por um serviço de envio de e-mails.</li>
        <li>
          Uma cópia do banco (contas e estatísticas, nunca código de aluno) é feita toda semana,
          criptografada, e guardada por 90 dias, para recuperar os dados se algo der errado. Só o
          desenvolvedor da plataforma tem a chave que a abre.
        </li>
        <li>
          Os registros técnicos não guardam código, senhas, tokens nem o IP. O IP é usado só na memória
          do servidor, para o limite de requisições, e some em até 2 minutos.
        </li>
      </ul>

      <h3 className="text-lg font-semibold">Saída da equipe</h3>
      <p>
        Uma conta removida não é apagada: perde o acesso e as sessões, e os dados ficam guardados para
        que a pessoa possa voltar à equipe, como acontece com monitores em outros períodos, sem um
        novo cadastro. Uma conta fora da equipe (removida, recusada ou à espera de aprovação) que passa
        365 dias sem nenhuma atividade é apagada, e o e-mail fica livre para um novo cadastro; um
        cadastro que não confirma o e-mail é apagado em 48 horas. Para corrigir os seus dados, use o
        perfil; para outros pedidos
        sobre eles, fale com o desenvolvedor da plataforma ou com a coordenação da disciplina.
      </p>

      <Link to="/" className="text-sm text-blue-700 underline dark:text-blue-300">
        Voltar ao início
      </Link>
    </article>
  );
}
