from marshmallow import Schema, fields, validate, ValidationError

class LoginExtratoSchema(Schema):
    """Schema de validação para login via extrato."""
    matricula = fields.Str(
        required=True,
        allow_none=False,
        validate=validate.Length(min=1),
        error_messages={'required': 'Matrícula é obrigatória'}
    )
    cpf = fields.Str(
        required=True,
        allow_none=False,
        validate=[
            validate.Regexp(r'^\d{5,6}$', error="CPF deve conter 5 ou 6 dígitos numéricos")
        ],
        error_messages={'required': 'CPF é obrigatório'}
    )


class ExtratoMesAnoSchema(Schema):
    """Schema para entrada de mes_ano (MM-YYYY)."""
    mes_ano = fields.Str(
        required=True,
        allow_none=False,
        validate=[
            validate.Length(equal=7, error="mes_ano deve ter 7 caracteres"),
            validate.Regexp(r'^[0-1][0-9]-[0-9]{4}$', error="Formato inválido, use MM-YYYY")
        ],
        error_messages={'required': 'mes_ano é obrigatório'}
    )


class CodigoCompraSchema(Schema):
    senha = fields.Str(required=True, validate=validate.Length(min=3))
    email = fields.Email(required=True)
    celular = fields.Str(required=True, validate=validate.Length(min=8, max=20))
    nova_senha = fields.Str(load_default=None, allow_none=True)
    cpf = fields.Str(
        required=True,
        allow_none=False,
        validate=[
            validate.Regexp(r'^\d{5,6}$', error="CPF deve conter 5 ou 6 dígitos numéricos")
        ],
        error_messages={'required': 'CPF é obrigatório'}
    )