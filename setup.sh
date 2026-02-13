pip install uv
uv pip install -r extra-req.txt --no-deps
uv pip install -r requirements.txt

# clientside installation
cd client
npm install three @pixiv/three-vrm @pixiv/three-vrm-animation


### extra for ntlk
# python - <<PYCODE
# import nltk
# for pkg in ["averaged_perceptron_tagger", "cmudict"]:
#     nltk.download(pkg)
# PYCODE
