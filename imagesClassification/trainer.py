import os
import argparse
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Input

def train_model(data_dir, img_height=224, img_width=224, batch_size=16, epochs=10):
    # Prepare the image data generators
    train_datagen = ImageDataGenerator(rescale=1./255, validation_split=0.2)

    train_generator = train_datagen.flow_from_directory(
        data_dir,
        target_size=(img_height, img_width),
        batch_size=batch_size,
        class_mode='binary',
        subset='training'
    )

    validation_generator = train_datagen.flow_from_directory(
        data_dir,
        target_size=(img_height, img_width),
        batch_size=batch_size,
        class_mode='binary',
        subset='validation'
    )

    # Build the CNN model using Input layer
    model = Sequential([
        Input(shape=(img_height, img_width, 3)),
        Conv2D(32, (3, 3), activation='relu'),
        MaxPooling2D(pool_size=(2, 2)),
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D(pool_size=(2, 2)),
        Flatten(),
        Dense(128, activation='relu'),
        Dense(1, activation='sigmoid')  # Binary classification
    ])

    # Compile the model
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

    # Train the model
    model.fit(train_generator, validation_data=validation_generator, epochs=epochs)

    # Save the trained model in the same directory as the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(script_dir, 'advertisement_classifier.h5')
    model.save(model_path)
    print(f"Model saved at: {model_path}")

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Train a CNN model to classify images of ads vs. matches.")
    parser.add_argument('data_dir', type=str, help='Path to the dataset folder containing images in subfolders.')

    # Parse the arguments
    args = parser.parse_args()

    # Train the model using the dataset directory
    train_model(data_dir=args.data_dir)
