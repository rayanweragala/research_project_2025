#!/bin/bash

mkdir -p /opt/research_project/models

cd /opt/research_project/models

echo "Downloading MobileNet SSD model (this may take a few minutes)..."
echo ""

wget --no-check-certificate https://storage.googleapis.com/download.tensorflow.org/models/object_detection/ssd_mobilenet_v2_coco_2018_03_29.tar.gz -O model.tar.gz

if [ -f "model.tar.gz" ]; then
    echo "Extracting model..."
    tar -xzf model.tar.gz
    
    if [ -f "ssd_mobilenet_v2_coco_2018_03_29/frozen_inference_graph.pb" ]; then
        mv ssd_mobilenet_v2_coco_2018_03_29/frozen_inference_graph.pb ./frozen_inference_graph.pb
        echo "Model file extracted successfully"
    fi
    
    rm -rf ssd_mobilenet_v2_coco_2018_03_29
    rm model.tar.gz
else
    echo "Primary download failed. Trying alternative source..."
    
    wget https://github.com/opencv/opencv_extra/raw/4.x/testdata/dnn/ssd_mobilenet_v2_coco_2018_03_29.pb -O frozen_inference_graph.pb
fi

if [ ! -f "ssd_mobilenet_v2_coco_2018_03_29.pbtxt" ]; then
    echo ""
    echo "Downloading config file..."
    wget https://raw.githubusercontent.com/opencv/opencv_extra/master/testdata/dnn/ssd_mobilenet_v2_coco_2018_03_29.pbtxt -O ssd_mobilenet_v2_coco_2018_03_29.pbtxt
fi

echo ""
echo "=========================================="
echo "Download Complete"
echo "=========================================="
echo ""
echo "Files in directory:"
ls -lh

echo ""
echo "Verifying files..."
if [ -f "frozen_inference_graph.pb" ] && [ -f "ssd_mobilenet_v2_coco_2018_03_29.pbtxt" ]; then
    pb_size=$(stat -c%s frozen_inference_graph.pb 2>/dev/null)
    if [ "$pb_size" -gt 1000000 ]; then
        echo "SUCCESS: Model file present: $(du -h frozen_inference_graph.pb | cut -f1)"
        echo "SUCCESS: Config file present: $(du -h ssd_mobilenet_v2_coco_2018_03_29.pbtxt | cut -f1)"
        echo ""
    else
        echo "ERROR: Model file is too small (corrupted download)"
        echo "Size: $pb_size bytes"
    fi
else
    echo "ERROR: Download incomplete"
    echo "Missing required files"
fi
