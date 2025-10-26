from marshmallow import Schema, fields, validate

class LoginConvenioSchema(Schema):
    usuario = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    senha = fields.Str(required=True, validate=validate.Length(min=3, max=100))

class MesAnoSchema(Schema):
    # Accept only months 01..12 and a 4-digit year
    mes_ano = fields.Str(required=True, validate=validate.Regexp(r'^(0[1-9]|1[0-2])-\d{4}$'))

class CodigoEmailSchema(Schema):
    email = fields.Email(required=True)

class AlterarSenhaCodigoSchema(Schema):
    codigo = fields.Str(required=True, validate=validate.Length(equal=6))
    nova_senha = fields.Str(required=True, validate=validate.Length(min=6))

class AlterarSenhaEsqueceuSchema(AlterarSenhaCodigoSchema):
    pass

class LimiteRequestSchema(Schema):
    matricula = fields.Str(required=True, validate=validate.Length(min=3, max=15))
    valor = fields.Str(required=True)  # valor monetário string "1.234,56" ou "100"
    nr_parcelas = fields.Int(required=True, validate=validate.Range(min=1, max=96))

class VendaSenhaSchema(Schema):
    matricula = fields.Str(required=True)
    valor = fields.Str(required=True)
    nr_parcelas = fields.Int(required=True, validate=validate.Range(min=1, max=96))
    tipo = fields.Str(required=True)  # tipo do sócio (impacta indicador consignatária)
    sequencia = fields.Int(load_default=None)
    mes = fields.Int(required=True, validate=validate.Range(min=1, max=12))
    ano = fields.Int(required=True, validate=validate.Range(min=2000, max=2100))
    saldo = fields.Float(required=True)
    cpf = fields.Str(load_default=None)
    matricula_atual = fields.Str(load_default=None)
    celular = fields.Str(load_default=None)
    associado = fields.Str(load_default=None)
    # usado apenas para compor mensagem de confirmação no WhatsApp
    id_compra = fields.Str(load_default=None)

