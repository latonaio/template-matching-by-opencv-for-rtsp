# core.py  

## 返す環境変数 : なかった場合のDEFAULT  

  ・SERVICE : template-matching-by-opencv-for-rtsp  
  ・DEVICE_NAME :  
  ・CAMERA_SERVICE : stream-usb-video-by-rtsp  
  ・PROCESS_NUM : 0  


## Template更新処理:

  kanbanのconnection_keyを獲得->connection_keyが”template-{PROCESS_NUM}と一致しているか確認(一致しなかった場合kanbanの値を1つ増やす)”->templates,template_timestampが共にNoneでないとき->templateにrecursive_cast_to_intしたものをリストとして返す->

 ### recusive_cast_to_int(template)
  template_imageとimageのtrim_pointsを返す.  
 ### cast_trim_points_to_int(trim_points)
  trim_pointsをint型に変換して返す.  

 ## main処理
  1.キューを取得する.
  2.パイプラインを構築する.   
  3.マッチングサーバーを立ち上げる.  
  4.


# streaming_matching
 
## Class

 ### RequestType
  Array,Template,WaitFitnessに値を割り振る.

 ### RequestContainer
  入力の型を振り分けるためのクラス.

 ### MatchingFromStreamingProcess
  マッチング処理を並列で実行するためのクラス

 ### MatchingFromStreaming
  ストリーミングからの入力でマッチング処理を行うためのクラス.  
  #### convert_loop(self, input_q, template_q, fitness_out_q, image_out_q, wait_q)  
   ##### while処理
    rcvはtemplate_qが空ならinput_qを取得,空でないならinput_qを取得  
	rcvがNoneならimage_out_q,fitness_out_qにNoneを挿入し処理終了  
	rcvがRequestContainerのインスタンスでないなら次のループを行う  
	rcvの型がArrayの場合,フィッティングを行い,合格ならfitness_out_qに結果を書き込む.また,wait_timestampとtemplate_timestampがどちらも存在するならwait_timestampとtemplate_timestampの同一判定を行う.同一であり,wait_qが空でなければwait_qにフィッティングの結果を書き込み,wait_timestampを削除する.  
	フィッティング結果の画像が得られたならばimage_out_qにフィッティング結果の画像を追加する.
	rcvの型がTemplateの場合,template及びwait_timestampを設定する.

   #### get_multiple_fitness(self, array)
    matcherのget_multiple_fitnessから結果を得て合否判定を行う.

   ### set_templates(self, templates, template_timestamp)
    templateデータを取得する.

   ### set_wait_timestamp(self,timestamp)
	wait_timestampにtimestampを設定する.

   ### unset_wait_timestamp(self)
    wait_timestampをNoneにする.

	# matcher_settings
 ## ImageSettings
  ### __init__処理  
	入力dataからpath,trim_points,trim_points_ratioを取得する.  

  ### calc_trim_points(self, image_width, image_height)  
	trim_pointsがNoneだった場合,new_trim_pointsを引数を使って設定する.  
	trim_points_ratioがNoneだった場合,new_trim_pointsをtrim_pointsに設定する.  
	trim_points,trim_points_ratioが設定されていた場合,画像サイズ*割合でnew_trim_pointsを設定する.  
  new_trim_pointsを返す.

 ## MatcherSettings
	template_dataの各keyに対応する画像のインスタンスを生成.


# matcher

 ### get_img_with_fitness(results, image)  
  matching_rateがpass_threshold(合格閾値?)より大きければdrawに用いる色をBLUEにする.それ以外の場合REDにする.  
  入力imageに上記の色を用いて矩形を描く.入力imageに上記の色を用いてtextを書く.  
  矩形/textを描いたimageを返す.  

 ## Template  
  ### set_template(self, template_data)  
	template_dataの各キーに対応する画像のインスタンスを生成.  
	template_imageのパスを読み込んで画像の配列,縦横の大きさを取得.  
	画像の大きさからtrim_pointsを取得し,画像を切り抜く.  
	画像をモノクロ処理する.

 ## Matcher  

  ### set_templates(self, templates, template_timestamp)  
   入力したtemplatesを全て前述したTemplateクラスによって処理する.処理結果はnew_templatesに格納する.全てのtemplatesについて処理が終わったらtemplatesをnew_templatesに置き換える.  

  ### _set_trim_image(self, template)  
   画像,あるいはストリーミング画像のサイズを取得し,上記のcalc_trim_points()に渡してtrim_pointsを取得する.取得したtrim_pointsを使用して画像を切り抜く.  

  ### _set_image(self, image)  

  ### _load_image(self, image_path)  

  ### _validate_image_size(self, template)  

  ### _run_template_matching(self, template)  

  ### get_multiple_fitness(self, image)  

# gst  

 ### get_now_datetime_string()  
  現在時刻をマイクロ秒(3桁)までstr型で取得する.  

 ### get_pipe(source_url, width, height)  
  

 ## GstRtspProcess  
  GstRtspの処理を並列で実行させるためのクラス  

 ## GstRtsp  
 ### reset_timeout(self)  
  unset_timeout(),set_timeout()を実行する.  

 ### unset_timeout(self)  
  underrun_timeout_idがNoneでないならサーバーへの接続を終了し,underrun_timeout_idをNoneにする.  

 ### set_timeout(self)  
  timeout関数を作成  

 ### timeout(self)  
  timeoutログを表示しretry_to_connect()を実行する.  

 ### start(self, queue)  
  入力キューに対して各種必要な処理を実行する.  

 ### try_to_connect(self)  
  

 ### retry_to_connect(self)  

 ### stop(self)  

 ### on_array_data(self, sink, data)  

 ### on_message(self, bus, message)  
