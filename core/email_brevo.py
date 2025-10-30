"""
Módulo de envio de emails usando Brevo (Sendinblue)
Substitui Flask-Mail com API mais confiável
"""

import os
import logging
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


class BrevoEmailSender:
    """
    Classe para envio de emails via Brevo API
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa o cliente Brevo
        
        Args:
            api_key: Chave de API do Brevo (se None, busca em variável de ambiente)
        """
        self.api_key = api_key or os.getenv('BREVO_API_KEY')
        
        if not self.api_key:
            raise ValueError("BREVO_API_KEY não configurada")
        
        # Configurar cliente Brevo
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = self.api_key
        
        self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )
        
        # Remetente padrão (DEVE ser email validado no Brevo)
        # elias_curitiba@hotmail.com está validado automaticamente na conta Brevo
        self.default_sender = {
            "email": os.getenv('MAIL_DEFAULT_SENDER', 'elias_curitiba@hotmail.com'),
            "name": os.getenv('MAIL_DEFAULT_NAME', 'ConsigExpress')
        }
        
        logger.info("✅ Cliente Brevo inicializado")
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        sender_email: Optional[str] = None,
        sender_name: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> Dict:
        """
        Envia um email via Brevo
        
        Args:
            to_email: Email do destinatário
            subject: Assunto do email
            html_content: Conteúdo HTML do email
            text_content: Conteúdo texto plano (opcional)
            sender_email: Email do remetente (padrão: MAIL_DEFAULT_SENDER)
            sender_name: Nome do remetente (padrão: MAIL_DEFAULT_NAME)
            reply_to: Email para resposta (opcional)
        
        Returns:
            Dict com resultado do envio
        
        Raises:
            Exception: Se houver erro no envio
        """
        try:
            # Configurar remetente
            sender = {
                "email": sender_email or self.default_sender["email"],
                "name": sender_name or self.default_sender["name"]
            }
            
            # Configurar destinatário
            to = [{"email": to_email}]
            
            # Montar email
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=to,
                sender=sender,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                reply_to={"email": reply_to} if reply_to else None
            )
            
            # Enviar
            logger.info(f"📧 Enviando email para {to_email}")
            api_response = self.api_instance.send_transac_email(send_smtp_email)
            
            logger.info(f"✅ Email enviado com sucesso! Message ID: {api_response.message_id}")
            
            return {
                "success": True,
                "message_id": api_response.message_id,
                "to": to_email,
                "subject": subject
            }
            
        except ApiException as e:
            error_msg = f"❌ Erro Brevo API: {e.status} - {e.reason}"
            logger.error(error_msg)
            logger.error(f"Body: {e.body}")
            
            raise Exception(f"Falha ao enviar email via Brevo: {e.reason}")
        
        except Exception as e:
            error_msg = f"❌ Erro inesperado: {str(e)}"
            logger.error(error_msg)
            raise
    
    def send_codigo_seguranca(
        self,
        to_email: str,
        codigo: str,
        usuario: str,
        validade_minutos: int = 10
    ) -> Dict:
        """
        Envia email com código de segurança para redefinição de senha
        
        Args:
            to_email: Email do destinatário
            codigo: Código de segurança (6 dígitos)
            usuario: Nome de usuário
            validade_minutos: Validade do código em minutos
        
        Returns:
            Dict com resultado do envio
        """
        subject = "Código de Segurança - ConsigExpress"
        
        # HTML moderno e responsivo
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 0;
                    background-color: #f4f4f4;
                }}
                .container {{
                    max-width: 600px;
                    margin: 40px auto;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 30px 20px;
                    text-align: center;
                    color: white;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 600;
                }}
                .content {{
                    padding: 40px 30px;
                }}
                .codigo-box {{
                    background: #f8f9fa;
                    border: 2px dashed #667eea;
                    border-radius: 8px;
                    padding: 30px;
                    margin: 30px 0;
                    text-align: center;
                }}
                .codigo {{
                    font-size: 48px;
                    font-weight: bold;
                    color: #667eea;
                    letter-spacing: 8px;
                    font-family: 'Courier New', monospace;
                    margin: 10px 0;
                }}
                .info {{
                    background: #e7f3ff;
                    border-left: 4px solid #2196F3;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .warning {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    font-size: 14px;
                    color: #6c757d;
                }}
                @media (max-width: 600px) {{
                    .container {{
                        margin: 20px 10px;
                    }}
                    .content {{
                        padding: 30px 20px;
                    }}
                    .codigo {{
                        font-size: 36px;
                        letter-spacing: 4px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 ConsigExpress</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Sistema de Consignação</p>
                </div>
                
                <div class="content">
                    <h2 style="color: #333; margin-top: 0;">Olá, {usuario}!</h2>
                    
                    <p>Você solicitou a redefinição de senha. Use o código abaixo para continuar:</p>
                    
                    <div class="codigo-box">
                        <p style="margin: 0; color: #666; font-size: 14px; text-transform: uppercase;">Seu código de segurança</p>
                        <div class="codigo">{codigo}</div>
                        <p style="margin: 0; color: #666; font-size: 14px;">Válido por {validade_minutos} minutos</p>
                    </div>
                    
                    <div class="info">
                        <strong>ℹ️ Como usar:</strong><br>
                        1. Copie o código acima<br>
                        2. Volte para a página de redefinição de senha<br>
                        3. Cole o código no campo indicado<br>
                        4. Crie sua nova senha
                    </div>
                    
                    <div class="warning">
                        <strong>⚠️ Atenção:</strong><br>
                        • Este código expira em <strong>{validade_minutos} minutos</strong><br>
                        • Não compartilhe este código com ninguém<br>
                        • Se você não solicitou esta redefinição, ignore este email
                    </div>
                    
                    <p style="color: #666; font-size: 14px; margin-top: 30px;">
                        Se tiver problemas, entre em contato com o suporte.
                    </p>
                </div>
                
                <div class="footer">
                    <p style="margin: 5px 0;">
                        <strong>ConsigExpress</strong><br>
                        A.S.P.M.A. - Associação dos Servidores Públicos Municipais de Adamantina
                    </p>
                    <p style="margin: 10px 0 0 0; font-size: 12px; color: #999;">
                        Este é um email automático. Por favor, não responda.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Versão texto plano (fallback)
        text_content = f"""
        ConsigExpress - Código de Segurança
        
        Olá, {usuario}!
        
        Você solicitou a redefinição de senha.
        
        Seu código de segurança: {codigo}
        
        Este código é válido por {validade_minutos} minutos.
        
        ATENÇÃO:
        - Não compartilhe este código com ninguém
        - Se você não solicitou esta redefinição, ignore este email
        
        ---
        ConsigExpress - A.S.P.M.A.
        """
        
        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )


# Função helper para facilitar uso
def send_codigo_seguranca(to_email: str, codigo: str, usuario: str) -> Dict:
    """
    Função helper para enviar código de segurança
    
    Args:
        to_email: Email do destinatário
        codigo: Código de segurança
        usuario: Nome de usuário
    
    Returns:
        Dict com resultado do envio
    """
    sender = BrevoEmailSender()
    return sender.send_codigo_seguranca(to_email, codigo, usuario)
