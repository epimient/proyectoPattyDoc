from tensorflow.keras.layers import Dense, Input
from tensorflow.keras.models import Model


def build_model(input_dim: int, output_dims: list):
    inputs = Input(shape=(input_dim,))
    x = Dense(128, activation="relu")(inputs)
    x = Dense(64, activation="relu")(x)
    output1 = Dense(output_dims[0], activation="softmax", name="phase1")(x)
    output2 = Dense(output_dims[1], activation="softmax", name="phase2")(x)
    output3 = Dense(output_dims[2], activation="softmax", name="phase3")(x)
    model = Model(inputs=inputs, outputs=[output1, output2, output3])
    model.compile(
        optimizer="adam",
        loss={
            "phase1": "categorical_crossentropy",
            "phase2": "categorical_crossentropy",
            "phase3": "categorical_crossentropy",
        },
        metrics={
            "phase1": "accuracy",
            "phase2": "accuracy",
            "phase3": "accuracy",
        },
    )
    return model
