#!/usr/bin/env python3
"""
ScamShield - Sample Model Training Pipeline
Quick start guide for training a phishing detection model
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score,
    roc_curve, precision_recall_curve
)
import matplotlib.pyplot as plt
import seaborn as sns

# Set style
sns.set_style("whitegrid")

class EmailPhishingDetector:
    """Train and evaluate phishing detection models"""
    
    def __init__(self, data_path='email_dataset.csv'):
        """Initialize detector with dataset"""
        print("📊 Loading dataset...")
        self.df = pd.read_csv(data_path)
        print(f"✓ Loaded {len(self.df)} emails")
        
        self.vectorizer = None
        self.model = None
        self.scaler = None
        
    def explore_data(self):
        """Basic data exploration"""
        print("\n" + "="*50)
        print("DATA EXPLORATION")
        print("="*50)
        
        print(f"\nDataset shape: {self.df.shape}")
        print(f"\nLabel distribution:")
        print(self.df['label'].value_counts())
        print(f"\nLabel percentage:")
        print(self.df['label'].value_counts(normalize=True) * 100)
        
        print("\n📊 Phishing vs Legitimate Statistics:")
        for label in ['phishing', 'legitimate']:
            data = self.df[self.df['label'] == label]
            print(f"\n{label.upper()}:")
            print(f"  - Average word count: {data['word_count'].mean():.1f}")
            print(f"  - Has links: {data['has_links'].sum()} ({data['has_links'].mean()*100:.1f}%)")
            print(f"  - Avg suspicious links: {data['suspicious_links_count'].mean():.2f}")
            print(f"  - Avg urgency indicators: {data['urgency_indicators_count'].mean():.2f}")
            print(f"  - Avg suspicious keywords: {data['suspicious_keywords_count'].mean():.2f}")
    
    def prepare_features(self):
        """Prepare text and numerical features"""
        print("\n" + "="*50)
        print("FEATURE PREPARATION")
        print("="*50)
        
        # Text vectorization (TF-IDF)
        print("\n📝 Vectorizing email text...")
        self.vectorizer = TfidfVectorizer(
            max_features=100,
            lowercase=True,
            stop_words='english',
            ngram_range=(1, 2)
        )
        text_features = self.vectorizer.fit_transform(self.df['body'])
        
        # Numerical features
        print("📊 Preparing numerical features...")
        numerical_features = self.df[[
            'word_count',
            'has_links',
            'suspicious_links_count',
            'urgency_indicators_count',
            'suspicious_keywords_count',
            'has_sender_spoofing',
            'has_capitals_excessive'
        ]].values
        
        # Scale numerical features
        self.scaler = StandardScaler()
        numerical_features = self.scaler.fit_transform(numerical_features)
        
        # Combine features
        from scipy.sparse import hstack
        X = hstack([text_features, numerical_features])
        
        print(f"✓ Total features: {X.shape[1]}")
        print(f"  - Text features (TF-IDF): {text_features.shape[1]}")
        print(f"  - Numerical features: {numerical_features.shape[1]}")
        
        return X
    
    def train_model(self, X, model_type='naive_bayes'):
        """Train classification model"""
        print("\n" + "="*50)
        print("MODEL TRAINING")
        print("="*50)
        
        # Prepare labels
        y = (self.df['label'] == 'phishing').astype(int)
        
        # Split data
        print("\n🔀 Splitting data (80/20 train/test)...")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        print(f"  - Training set: {X_train.shape[0]} emails")
        print(f"  - Test set: {X_test.shape[0]} emails")
        
        # Train model
        print(f"\n🤖 Training {model_type} model...")
        if model_type == 'naive_bayes':
            self.model = MultinomialNB()
        elif model_type == 'random_forest':
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        
        self.model.fit(X_train, y_train)
        print("✓ Model trained successfully!")
        
        return X_train, X_test, y_train, y_test
    
    def evaluate_model(self, X_test, y_test):
        """Evaluate model performance"""
        print("\n" + "="*50)
        print("MODEL EVALUATION")
        print("="*50)
        
        # Predictions
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        
        # Metrics
        print("\n📊 Classification Report:")
        print(classification_report(
            y_test, y_pred,
            target_names=['Legitimate', 'Phishing'],
            digits=4
        ))
        
        # Confusion Matrix
        cm = confusion_matrix(y_test, y_pred)
        print("\n🔲 Confusion Matrix:")
        print(f"  TN: {cm[0,0]}  FP: {cm[0,1]}")
        print(f"  FN: {cm[1,0]}  TP: {cm[1,1]}")
        
        # ROC-AUC
        roc_auc = roc_auc_score(y_test, y_pred_proba)
        print(f"\n📈 ROC-AUC Score: {roc_auc:.4f}")
        
        # Visualization
        self._plot_results(y_test, y_pred, y_pred_proba, cm)
        
        return y_pred, y_pred_proba
    
    def _plot_results(self, y_test, y_pred, y_pred_proba, cm):
        """Plot evaluation results"""
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # Confusion Matrix
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[0, 0])
        axes[0, 0].set_title('Confusion Matrix')
        axes[0, 0].set_ylabel('True Label')
        axes[0, 0].set_xlabel('Predicted Label')
        
        # ROC Curve
        fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
        auc = roc_auc_score(y_test, y_pred_proba)
        axes[0, 1].plot(fpr, tpr, label=f'ROC (AUC = {auc:.4f})')
        axes[0, 1].plot([0, 1], [0, 1], 'k--', label='Random')
        axes[0, 1].set_xlabel('False Positive Rate')
        axes[0, 1].set_ylabel('True Positive Rate')
        axes[0, 1].set_title('ROC Curve')
        axes[0, 1].legend()
        axes[0, 1].grid(alpha=0.3)
        
        # Prediction Distribution
        axes[1, 0].hist(y_pred_proba[y_test == 0], bins=20, alpha=0.7, label='Legitimate')
        axes[1, 0].hist(y_pred_proba[y_test == 1], bins=20, alpha=0.7, label='Phishing')
        axes[1, 0].set_xlabel('Predicted Probability (Phishing)')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].set_title('Prediction Score Distribution')
        axes[1, 0].legend()
        axes[1, 0].grid(alpha=0.3)
        
        # Precision-Recall Curve
        precision, recall, _ = precision_recall_curve(y_test, y_pred_proba)
        axes[1, 1].plot(recall, precision)
        axes[1, 1].set_xlabel('Recall')
        axes[1, 1].set_ylabel('Precision')
        axes[1, 1].set_title('Precision-Recall Curve')
        axes[1, 1].grid(alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('model_evaluation.png', dpi=150, bbox_inches='tight')
        print("\n✓ Saved evaluation plots to 'model_evaluation.png'")
        # Uncomment to display:
        # plt.show()
    
    def predict_email(self, subject, body):
        """Predict if an email is phishing"""
        if self.vectorizer is None or self.model is None:
            print("❌ Model not trained yet!")
            return None
        
        # Prepare email
        from scipy.sparse import hstack
        
        # Text features
        text_features = self.vectorizer.transform([body])
        
        # Numerical features (simplified)
        numerical_features = np.array([[
            len(body.split()),  # word_count
            1 if 'http' in body or 'bit.ly' in body else 0,  # has_links
            body.count('http'),  # suspicious_links_count
            sum([1 for phrase in ['urgent', 'verify', 'confirm', 'act now'] 
                 if phrase in body.lower()]),  # urgency_indicators
            sum([1 for word in ['verify', 'confirm', 'click', 'update', 'verify']
                 if word in body.lower()]),  # suspicious_keywords
            0,  # has_sender_spoofing
            sum(1 for c in body if c.isupper()) > len(body) * 0.3  # has_capitals_excessive
        ]])
        
        numerical_features = self.scaler.transform(numerical_features)
        
        # Combine
        X = hstack([text_features, numerical_features])
        
        # Predict
        prediction = self.model.predict(X)[0]
        probability = self.model.predict_proba(X)[0]
        
        return {
            'is_phishing': bool(prediction),
            'phishing_probability': float(probability[1]),
            'legitimate_probability': float(probability[0])
        }


def main():
    """Run complete pipeline"""
    # Initialize
    detector = EmailPhishingDetector('email_dataset.csv')
    
    # Explore
    detector.explore_data()
    
    # Prepare features
    X = detector.prepare_features()
    
    # Train
    X_train, X_test, y_train, y_test = detector.train_model(X, model_type='naive_bayes')
    
    # Evaluate
    y_pred, y_pred_proba = detector.evaluate_model(X_test, y_test)
    
    # Test prediction
    print("\n" + "="*50)
    print("SAMPLE PREDICTION")
    print("="*50)
    test_subject = "Urgent: Verify Your Account"
    test_body = "Click here immediately to verify your account before it gets suspended"
    result = detector.predict_email(test_subject, test_body)
    print(f"\nEmail: {test_subject}")
    print(f"Result: {result}")


if __name__ == "__main__":
    main()
