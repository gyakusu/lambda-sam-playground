"""Streamlit UI for uploading CSV data to S3 using np.linspace()."""

import io
import csv
from typing import Optional

import streamlit as st
import boto3
import numpy as np


def create_s3_client():
    """Create an S3 client using AWS credentials."""
    return boto3.client(
        "s3",
        aws_access_key_id=st.secrets.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=st.secrets.get("AWS_SECRET_ACCESS_KEY"),
        region_name=st.secrets.get("AWS_REGION", "us-east-1"),
    )


def generate_csv_from_linspace(
    start: float, stop: float, num: int, num_cols: int = 2
) -> str:
    """Generate CSV content using np.linspace() for multiple columns.
    
    Args:
        start: Start value for linspace
        stop: Stop value for linspace
        num: Number of samples to generate
        num_cols: Number of columns to create
        
    Returns:
        CSV string content
    """
    # Create linspace array
    data = np.linspace(start, stop, num)
    
    # Create a DataFrame with multiple columns
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    columns = [f"value_{i+1}" for i in range(num_cols)]
    writer.writerow(columns)
    
    # Write data rows (each column gets the same linspace data)
    for value in data:
        row = [value] * num_cols
        writer.writerow(row)
    
    return output.getvalue()


def upload_to_s3(bucket_name: str, s3_key: str, csv_content: str) -> bool:
    """Upload CSV content to S3.
    
    Args:
        bucket_name: S3 bucket name
        s3_key: S3 object key (path/filename)
        csv_content: CSV string content
        
    Returns:
        True if upload succeeded, False otherwise
    """
    try:
        client = create_s3_client()
        client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=csv_content.encode("utf-8"),
            ContentType="text/csv",
        )
        return True
    except Exception as e:
        st.error(f"S3 upload failed: {str(e)}")
        return False


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Lambda SAM Playground - CSV Upload",
        layout="centered",
    )
    
    st.title("📊 CSV Upload to S3 with np.linspace()")
    st.markdown(
        "Generate CSV data using NumPy's `linspace()` and upload to S3."
    )
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        bucket_name = st.text_input(
            "S3 Bucket Name",
            value="lambda-sam-playground-data",
            help="Target S3 bucket for upload",
        )
        s3_prefix = st.text_input(
            "S3 Path Prefix",
            value="streamlit",
            help="Folder path in S3 (e.g., 'streamlit', 'verification')",
        )
    
    # Main content area
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔢 linspace Parameters")
        start = st.number_input(
            "Start Value",
            value=0.0,
            step=1.0,
            help="Starting value of the sequence",
        )
        stop = st.number_input(
            "Stop Value",
            value=100.0,
            step=1.0,
            help="End value of the sequence",
        )
        num = st.slider(
            "Number of Samples",
            min_value=5,
            max_value=1000,
            value=50,
            step=5,
            help="How many evenly-spaced points to generate",
        )
        num_cols = st.slider(
            "Number of Columns",
            min_value=1,
            max_value=10,
            value=2,
            help="Number of columns in the generated CSV",
        )
    
    with col2:
        st.subheader("📋 Preview")
        csv_content = generate_csv_from_linspace(start, stop, num, num_cols)
        
        # Show preview of first few rows
        st.text_area(
            "CSV Preview (first 10 rows)",
            value="\n".join(csv_content.split("\n")[:11]),
            height=200,
            disabled=True,
            label_visibility="collapsed",
        )
    
    # Upload section
    st.divider()
    st.subheader("📤 Upload to S3")
    
    filename = st.text_input(
        "Filename",
        value="linspace_data.csv",
        help="Name of the CSV file to create in S3",
    )
    
    if st.button(
        "🚀 Upload to S3",
        use_container_width=True,
        type="primary",
    ):
        if not bucket_name:
            st.error("❌ Please specify a bucket name")
        elif not filename.endswith(".csv"):
            st.error("❌ Filename must end with .csv")
        else:
            # Construct full S3 path
            s3_key = f"{s3_prefix}/{filename}" if s3_prefix else filename
            
            with st.spinner("Uploading..."):
                if upload_to_s3(bucket_name, s3_key, csv_content):
                    st.success(
                        f"✅ Successfully uploaded to:\n`s3://{bucket_name}/{s3_key}`"
                    )
                    st.info(
                        "The Lambda function will process this file. "
                        "Check CloudWatch Logs for the results."
                    )
    
    # Statistics display
    st.divider()
    st.subheader("📊 Generated Data Statistics")
    
    # Parse CSV and show statistics
    lines = csv_content.strip().split("\n")
    header = lines[0].split(",")
    data_points = [float(line.split(",")[0]) for line in lines[1:]]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Rows", len(data_points))
    with col2:
        st.metric("Columns", num_cols)
    with col3:
        st.metric("Min Value", f"{min(data_points):.2f}")
    with col4:
        st.metric("Max Value", f"{max(data_points):.2f}")
    
    # Show the numpy linspace call
    st.code(
        f"np.linspace(start={start}, stop={stop}, num={num})",
        language="python",
    )


if __name__ == "__main__":
    main()
